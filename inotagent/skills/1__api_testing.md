---
name: api_testing
description: Test API endpoints, generate test cases, monitor health, and track performance metrics.
tags: [development, testing, api, monitoring]
source: awesome-openclaw-agents/agents/development/api-tester
---

## API Testing

> ~442 tokens

### Test Categories

- **Smoke tests:** Basic endpoint availability (GET /health -> 200)
- **Functional tests:** Correct behavior (POST /login -> returns token)
- **Validation tests:** Error handling (POST /login with empty password -> 400)
- **Performance tests:** Response time under load
- **Security tests:** Auth bypass, injection, rate limiting

### Endpoint Testing Checklist

1. Test API endpoints with various inputs
2. Validate response status codes and body structure
3. Check error handling for invalid inputs
4. Verify authentication and authorization
5. Include response times in all results

### Test Generation Workflow

1. Generate test cases from OpenAPI/Swagger specs
2. Create edge case tests (empty inputs, large payloads, special characters)
3. Build regression test suites
4. Suggest test coverage improvements

### Health Monitoring

1. Run periodic health checks on all endpoints
2. Track response times and latency trends
3. Alert on slow or failing endpoints (define threshold, e.g., >500ms)
4. Monitor uptime percentage

### Reporting Format

For each endpoint test:

```
Test N: <description>
  Input: <payload>
  Status: <code> (<time>ms)
  Response: <body summary>
  Result: PASS / FAIL / WARN - <reason>
```

Summary: X pass, Y warnings, Z failures. Avg response: Nms.

### Rules

- Test both happy path and error cases
- Verify response body structure, not just status codes
- Track trends over time (is it getting slower?)
- Test with realistic payloads
- Never run destructive tests (DELETE, DROP) without explicit permission
- Never test with production user data
- Do not overwhelm the API with too many concurrent requests
- Do not ignore intermittent failures (they signal real problems)
- Never skip authentication testing
