# Next Steps

## Fix Dashboard.test.tsx memory issue

The Dashboard test file (`frontend/src/components/Dashboard/__tests__/Dashboard.test.tsx`) crashes the Vitest worker process with a JavaScript heap out of memory error before any tests can run. Investigate the root cause (likely large mock data, infinite render loops, or missing test cleanup) and fix so all Dashboard tests pass within normal memory limits.
