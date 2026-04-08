"""Natural language query API endpoints."""

import json
import re
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from ..claude import ClaudeClient
from ..db import DatabaseManager
from ..middleware import limiter
from ..middleware.rate_limit import RATE_LIMIT_CLAUDE_API
from ..middleware.validation import validate_query_length, MAX_QUERY_LENGTH


router = APIRouter()


SQL_GENERATION_PROMPT = """You are a SQL expert assistant. Generate a safe, read-only DuckDB SQL query based on the user's natural language question.

Available tables and their schemas:

1. daily_metrics (date DATE PRIMARY KEY, sleep_hours DECIMAL, sleep_quality INTEGER 1-5, energy INTEGER 1-5, mood INTEGER 1-5, stress INTEGER 1-5, notes VARCHAR)

2. exercise_log (id VARCHAR, activity_id VARCHAR, date DATE, exercise_name VARCHAR, weight_kg DECIMAL, reps INTEGER, set_number INTEGER, duration_minutes INTEGER, distance_km DECIMAL, notes VARCHAR)

3. activities (id VARCHAR, date DATE, activity_type VARCHAR, duration_minutes INTEGER, notes VARCHAR)

4. food_log (id VARCHAR, date DATE, meal_type VARCHAR, time TIME, description VARCHAR, calories INTEGER, protein_g INTEGER, carbs_g INTEGER, fat_g INTEGER, notes VARCHAR)

5. tasks (id VARCHAR, date DATE, description VARCHAR, status VARCHAR, completed_at TIMESTAMP, category VARCHAR, priority INTEGER)

Rules:
- Only generate SELECT queries (no INSERT, UPDATE, DELETE, DROP, etc.)
- Use DuckDB SQL syntax
- Use appropriate date functions: CURRENT_DATE, DATE_SUB, DATE_TRUNC, etc.
- For "last week", use: date >= CURRENT_DATE - INTERVAL 7 DAY
- For "this month", use: date >= DATE_TRUNC('month', CURRENT_DATE)
- For "this year", use: date >= DATE_TRUNC('year', CURRENT_DATE)
- Limit results to 100 rows unless user asks for more
- Return only the SQL query, nothing else

Example queries:
- "How much did I sleep last week?" -> SELECT date, sleep_hours FROM daily_metrics WHERE date >= CURRENT_DATE - INTERVAL 7 DAY ORDER BY date
- "What was my heaviest squat?" -> SELECT date, exercise_name, weight_kg, reps FROM exercise_log WHERE exercise_name ILIKE '%squat%' ORDER BY weight_kg DESC LIMIT 1
- "Show my exercise frequency by day" -> SELECT DAYNAME(date) as day_of_week, COUNT(*) as count FROM exercise_log GROUP BY DAYNAME(date), DAYOFWEEK(date) ORDER BY DAYOFWEEK(date)

User question: {question}

SQL query:"""


RESPONSE_FORMATTING_PROMPT = """You are a helpful assistant that explains data query results in natural language.

Given the user's question and the query results, provide a clear, conversational answer.
- Be concise and direct
- Highlight key insights from the data
- If the data is empty, say so helpfully
- Use actual numbers from the results
- Format dates nicely (e.g., "January 5th" instead of "2026-01-05")

User question: {question}

Query results (as JSON):
{results}

Provide a natural language answer:"""


class QueryRequest(BaseModel):
    """Request for natural language query."""

    question: str = Field(..., min_length=1, max_length=MAX_QUERY_LENGTH)


class QueryResponse(BaseModel):
    """Response from natural language query."""

    answer: str
    sql: Optional[str] = None
    data: Optional[list[dict[str, Any]]] = None
    columns: Optional[list[str]] = None
    row_count: int = 0
    error: Optional[str] = None


def get_db(request: Request) -> DatabaseManager:
    """Get database manager from app state."""
    return request.app.state.db


def get_claude(request: Request) -> ClaudeClient:
    """Get Claude client from app state."""
    return request.app.state.claude


def validate_sql(sql: str) -> bool:
    """Validate that SQL is a safe read-only query.

    Args:
        sql: SQL query string

    Returns:
        True if safe, False otherwise
    """
    # Normalize SQL for checking
    normalized = sql.upper().strip()

    # Must start with SELECT or WITH (for CTEs)
    if not (normalized.startswith("SELECT") or normalized.startswith("WITH")):
        return False

    # Block dangerous keywords
    dangerous = [
        "INSERT",
        "UPDATE",
        "DELETE",
        "DROP",
        "TRUNCATE",
        "ALTER",
        "CREATE",
        "GRANT",
        "REVOKE",
        "EXEC",
        "EXECUTE",
        "ATTACH",
        "DETACH",
        "COPY",
        "LOAD",
        "INSTALL",
    ]

    for keyword in dangerous:
        # Check for keyword as whole word
        if re.search(rf"\b{keyword}\b", normalized):
            return False

    return True


def extract_sql_from_response(response: str) -> str:
    """Extract SQL query from Claude's response.

    Args:
        response: Claude's response text

    Returns:
        Extracted SQL query
    """
    # Try to find SQL in code blocks first
    code_block_match = re.search(r"```(?:sql)?\s*([\s\S]*?)```", response)
    if code_block_match:
        return code_block_match.group(1).strip()

    # Otherwise, look for SELECT statement
    select_match = re.search(r"((?:WITH|SELECT)[\s\S]+?)(?:;|$)", response, re.IGNORECASE)
    if select_match:
        return select_match.group(1).strip().rstrip(";")

    # Fall back to the whole response
    return response.strip()


@router.post("/query/natural", response_model=QueryResponse)
@limiter.limit(RATE_LIMIT_CLAUDE_API)
async def natural_language_query(
    request: QueryRequest,
    http_request: Request,
    db: DatabaseManager = Depends(get_db),
    claude: ClaudeClient = Depends(get_claude),
) -> QueryResponse:
    """Process a natural language query against the database.

    1. Use Claude to interpret the query and generate SQL
    2. Validate and execute SQL against DuckDB
    3. Format results with Claude
    4. Return structured response

    Args:
        request: Query request with natural language question
        db: Database manager
        claude: Claude client

    Returns:
        Query response with answer and data
    """
    if not claude.is_configured:
        raise HTTPException(
            status_code=503,
            detail="Claude API not configured. Set ANTHROPIC_API_KEY environment variable.",
        )

    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    try:
        # Step 1: Generate SQL from natural language
        sql_prompt = SQL_GENERATION_PROMPT.format(question=question)
        sql_response = await claude._call_with_retry(
            claude._create_message,
            model=claude.model_fast,
            max_tokens=1024,
            messages=[{"role": "user", "content": sql_prompt}],
        )
        raw_sql = sql_response.content[0].text
        sql = extract_sql_from_response(raw_sql)

        # Step 2: Validate SQL is safe
        if not validate_sql(sql):
            return QueryResponse(
                answer="I can only help with read-only queries. Please rephrase your question.",
                error="Generated SQL was not a safe read-only query",
            )

        # Step 3: Execute SQL against DuckDB
        try:
            result = db.execute(sql)
            columns = [desc[0] for desc in result.description]
            rows = result.fetchall()

            # Convert to list of dicts for JSON serialization
            data = []
            for row in rows[:100]:  # Limit to 100 rows
                row_dict = {}
                for i, col in enumerate(columns):
                    val = row[i]
                    # Handle special types
                    if hasattr(val, "isoformat"):
                        val = val.isoformat()
                    elif isinstance(val, (bytes, bytearray)):
                        val = val.decode("utf-8", errors="replace")
                    row_dict[col] = val
                data.append(row_dict)

            row_count = len(rows)

        except Exception as e:
            return QueryResponse(
                answer=f"I had trouble running that query. The database returned an error: {str(e)}",
                sql=sql,
                error=str(e),
            )

        # Step 4: Format results with Claude
        if not data:
            answer = "I didn't find any data matching your question. This might be because no data has been recorded yet, or the criteria didn't match any entries."
        else:
            # Prepare results for formatting
            results_json = json.dumps(data[:20], indent=2, default=str)  # Limit context size
            format_prompt = RESPONSE_FORMATTING_PROMPT.format(
                question=question, results=results_json
            )

            format_response = await claude._call_with_retry(
                claude._create_message,
                model=claude.model_fast,
                max_tokens=1024,
                messages=[{"role": "user", "content": format_prompt}],
            )
            answer = format_response.content[0].text

        return QueryResponse(
            answer=answer,
            sql=sql,
            data=data,
            columns=columns,
            row_count=row_count,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")
