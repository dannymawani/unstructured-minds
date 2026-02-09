# 05 - Anthropic API Token Strategy

This is the hardest problem to get right. Claude API calls are the most expensive part of the stack, and the most valuable feature of the product.

## The Problem

Current usage per active user per day (estimated):

| Operation | Model | Calls/day | Avg tokens | Cost/call | Daily cost |
|-----------|-------|-----------|------------|-----------|------------|
| Data extraction | Haiku 4.5 | 5-10 | 2K in / 1K out | ~$0.003 | $0.015-0.03 |
| NL queries | Sonnet 4.5 | 3-5 | 3K in / 2K out | ~$0.025 | $0.075-0.125 |
| Note assist | Sonnet 4.5 | 2-3 | 2K in / 1K out | ~$0.015 | $0.030-0.045 |
| Insights | Sonnet 4.5 | 1-2 | 5K in / 3K out | ~$0.04 | $0.040-0.080 |
| **Total** | | **11-20** | | | **$0.16-0.28/day** |

That's roughly **$5-8/user/month** in API costs for an active user.

## Strategy: Hybrid Model

```
┌─────────────────────────────────────────────────┐
│              Free Tier (default)                 │
│                                                  │
│  • 50 AI operations/month                        │
│  • Uses OUR Anthropic key                        │
│  • Haiku for extraction (cheap)                  │
│  • Sonnet for queries (limited)                  │
│  • Good enough to try the product                │
│  • Cost to us: ~$1.50/user/month                │
│                                                  │
├─────────────────────────────────────────────────┤
│              BYO Key (unlimited)                 │
│                                                  │
│  • Unlimited AI operations                       │
│  • User provides their own Anthropic API key     │
│  • Key stored encrypted in Supabase              │
│  • All models available                          │
│  • Cost to us: $0                                │
│  • User pays Anthropic directly                  │
│                                                  │
├─────────────────────────────────────────────────┤
│              Pro Tier ($12/month)                 │
│                                                  │
│  • 500 AI operations/month                       │
│  • Uses OUR key with higher limits               │
│  • Priority processing                           │
│  • All models available                          │
│  • Cost to us: ~$5-8/user/month                 │
│  • Our margin: $4-7/user/month                  │
│                                                  │
└─────────────────────────────────────────────────┘
```

### Why This Hybrid Works

1. **Free tier gets people in the door.** 50 operations is enough for a week of moderate use. They'll see the value.
2. **BYO key removes friction for power users.** Many developers already have Anthropic keys. Let them use it.
3. **Pro tier captures users who want simplicity.** "I don't want to manage an API key, just charge me."

## Implementation

### 1. Usage Tracking Middleware

```python
# backend/src/middleware/usage.py
from supabase import AsyncClient

# Token costs (approximate, per 1M tokens)
MODEL_COSTS = {
    "claude-haiku-4-5-20251001": {"input": 1.00, "output": 5.00},
    "claude-sonnet-4-5-20250929": {"input": 3.00, "output": 15.00},
}

class UsageTracker:
    def __init__(self, supabase: AsyncClient):
        self.supabase = supabase

    async def log_usage(
        self,
        user_id: str,
        action: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
    ) -> None:
        costs = MODEL_COSTS.get(model, {"input": 3.0, "output": 15.0})
        cost_usd = (
            (input_tokens / 1_000_000) * costs["input"]
            + (output_tokens / 1_000_000) * costs["output"]
        )

        await self.supabase.table("usage_log").insert({
            "user_id": user_id,
            "action": action,
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_usd": cost_usd,
        }).execute()

    async def check_quota(self, user_id: str) -> dict:
        """Check if user has remaining quota."""
        user = await self.supabase.table("users").select("tier").eq("id", user_id).single().execute()
        tier = user.data["tier"]

        limits = {
            "free": 50,
            "pro": 500,
            "byo_key": float("inf"),
        }

        # Count this month's usage
        month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0)
        usage = await self.supabase.table("usage_log") \
            .select("id", count="exact") \
            .eq("user_id", user_id) \
            .gte("created_at", month_start.isoformat()) \
            .execute()

        used = usage.count
        limit = limits.get(tier, 50)

        return {
            "used": used,
            "limit": limit,
            "remaining": max(0, limit - used),
            "tier": tier,
        }
```

### 2. Smart Key Resolution

```python
# backend/src/claude/key_resolver.py

class AnthropicKeyResolver:
    """Determine which API key to use for a request."""

    def __init__(self, platform_key: str, supabase: AsyncClient):
        self.platform_key = platform_key
        self.supabase = supabase

    async def resolve(self, user_id: str) -> tuple[str, str]:
        """Returns (api_key, source) where source is 'platform' or 'user'."""

        # Check if user has a BYO key
        settings = await self.supabase.table("user_settings") \
            .select("anthropic_api_key") \
            .eq("user_id", user_id) \
            .single() \
            .execute()

        user_key = settings.data.get("anthropic_api_key")

        if user_key:
            decrypted = decrypt_api_key(user_key)
            return (decrypted, "user")

        return (self.platform_key, "platform")
```

### 3. Quota Enforcement

```python
# backend/src/middleware/quota.py

async def enforce_quota(user_id: str, tracker: UsageTracker, key_resolver: AnthropicKeyResolver):
    """Check quota before making an AI call."""
    api_key, source = await key_resolver.resolve(user_id)

    if source == "user":
        # BYO key: no limits from us
        return api_key

    # Platform key: check quota
    quota = await tracker.check_quota(user_id)

    if quota["remaining"] <= 0:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "Monthly AI quota exceeded",
                "used": quota["used"],
                "limit": quota["limit"],
                "tier": quota["tier"],
                "upgrade_options": [
                    {"tier": "byo_key", "description": "Add your own Anthropic API key for unlimited use"},
                    {"tier": "pro", "price": "$12/month", "limit": 500},
                ],
            }
        )

    return api_key
```

### 4. BYO Key Setup (Frontend)

```tsx
// Settings page component
function ApiKeySettings() {
  const [key, setKey] = useState('')
  const [saved, setSaved] = useState(false)

  const saveKey = async () => {
    await api.put('/settings/anthropic-key', { key })
    setSaved(true)
  }

  return (
    <div>
      <h3>Anthropic API Key</h3>
      <p>
        Add your own API key for unlimited AI operations.
        Get one at{' '}
        <a href="https://console.anthropic.com/settings/keys">
          console.anthropic.com
        </a>
      </p>
      <input
        type="password"
        placeholder="sk-ant-api03-..."
        value={key}
        onChange={(e) => setKey(e.target.value)}
      />
      <button onClick={saveKey}>Save Key</button>
      {saved && <span>Key saved and encrypted</span>}
    </div>
  )
}
```

### 5. Key Encryption

```python
# backend/src/security/encryption.py
from cryptography.fernet import Fernet

# ENCRYPTION_KEY stored in Railway env vars
fernet = Fernet(os.environ["ENCRYPTION_KEY"])

def encrypt_api_key(key: str) -> str:
    return fernet.encrypt(key.encode()).decode()

def decrypt_api_key(encrypted: str) -> str:
    return fernet.decrypt(encrypted.encode()).decode()
```

## Usage Dashboard (Frontend)

Show users their usage so there's no surprise:

```
┌─────────────────────────────────────────┐
│  AI Usage This Month                    │
│                                         │
│  ████████████░░░░░░░░  34 / 50 used     │
│                                         │
│  16 operations remaining                │
│  Resets Feb 1, 2026                     │
│                                         │
│  ┌─────────────────────────────────┐    │
│  │ Want unlimited?                  │    │
│  │                                  │    │
│  │ [Add Your API Key]  [Go Pro $12] │    │
│  └─────────────────────────────────┘    │
└─────────────────────────────────────────┘
```

## Anthropic API Best Practices

### 1. Use the Right Model for the Job

```python
MODEL_MAP = {
    "extraction": "claude-haiku-4-5-20251001",     # Cheap, fast, good enough
    "query": "claude-sonnet-4-5-20250929",          # Needs reasoning for SQL
    "note_assist": "claude-haiku-4-5-20251001",     # Simple text operations
    "insights": "claude-sonnet-4-5-20250929",       # Needs analytical depth
    "chat": "claude-sonnet-4-5-20250929",           # Conversational quality
}
```

### 2. Prompt Caching

Anthropic supports prompt caching. For repeated system prompts (extraction schemas, query instructions), cache them:

```python
# The system prompt for extraction is the same for every user.
# With prompt caching, we pay for it once, then ~90% discount on subsequent calls.
response = client.messages.create(
    model="claude-haiku-4-5-20251001",
    system=[{
        "type": "text",
        "text": EXTRACTION_SYSTEM_PROMPT,
        "cache_control": {"type": "ephemeral"}  # Cache for 5 minutes
    }],
    messages=[{"role": "user", "content": note_content}]
)
```

This can reduce costs by 50-80% for extraction calls.

### 3. Batch Extraction

Instead of extracting one note at a time, batch notes when a user first signs up or imports data:

```python
# Use Anthropic's Batches API for bulk extraction
batch = client.batches.create(
    requests=[
        {"custom_id": f"note_{i}", "params": {...}}
        for i, note in enumerate(notes)
    ]
)
# 50% discount on batch API pricing
```

### 4. Token Budget Per Request

Set `max_tokens` appropriately to avoid runaway costs:

```python
MAX_TOKENS = {
    "extraction": 2000,    # Structured data is compact
    "query": 1500,         # SQL + brief explanation
    "note_assist": 3000,   # Longer text generation
    "insights": 4000,      # Detailed analysis
}
```

## Revenue Math

| Scenario | Users | Free | BYO | Pro | Monthly Revenue | Monthly API Cost | Net |
|----------|-------|------|-----|-----|-----------------|------------------|-----|
| Launch | 100 | 80 | 15 | 5 | $60 | $140 | -$80 |
| Traction | 500 | 350 | 100 | 50 | $600 | $625 | -$25 |
| Growth | 2000 | 1200 | 500 | 300 | $3,600 | $2,300 | +$1,300 |
| Scale | 10000 | 5000 | 3000 | 2000 | $24,000 | $10,500 | +$13,500 |

The model becomes profitable around 1000-2000 users, assuming ~30% convert to either BYO or Pro.

## Fallback: Usage-Based Pricing

If the tier model doesn't work, pivot to usage-based:

```
$0.00 per extraction (Haiku)     → We eat this cost, it's pennies
$0.05 per query (Sonnet)         → Small charge per AI query
$0.02 per note assist (Haiku)    → Cheap
$0.10 per insight (Sonnet)       → Higher value, higher charge

Billing: Stripe usage-based billing, charged monthly
```

This is more complex to implement but aligns costs perfectly with revenue.
