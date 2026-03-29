---
name: api_documentation
description: Generate and maintain API documentation from code, including OpenAPI specs, usage examples, and sync reports.
tags: [development, documentation, api, openapi]
source: awesome-openclaw-agents/agents/development/api-documentation + docs-writer
---

## API Documentation

> ~758 tokens

### Endpoint Discovery Workflow

1. Scan codebase for route definitions (Express, FastAPI, Django, etc.)
2. Detect HTTP methods, URL patterns, and middleware
3. Identify request/response schemas from code and types
4. Map authentication and authorization requirements

### OpenAPI Spec Generation

1. Generate valid OpenAPI 3.0 YAML/JSON specifications
2. Define schemas for request bodies, query params, and responses
3. Document authentication schemes (Bearer, API key, OAuth2)
4. Create reusable component schemas for shared models
5. Add proper tags and groupings for endpoint organization

### Endpoint Documentation Template

```yaml
/api/v1/<resource>:
  <method>:
    summary: <one-line description>
    tags: [<group>]
    security:
      - bearerAuth: []
    requestBody:
      required: true
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/<SchemaName>'
          example:
            <realistic example payload>
    responses:
      <2xx>:
        description: <success description>
      400:
        description: Validation error
      401:
        description: Missing or invalid authentication
      404:
        description: Resource not found
      500:
        description: Internal server error
```

### Usage Examples Checklist

- Write cURL examples for every endpoint
- Generate language-specific SDK snippets (JavaScript, Python, Go)
- Include realistic sample payloads, not lorem ipsum
- Document pagination, filtering, and sorting patterns
- Show error handling with actual error response bodies

### Documentation Sync Report Format

```
API Documentation Sync Report
Date: <date>

NEW ENDPOINTS (<count>):
  <method> <path> -- <description> (no docs yet)

BREAKING CHANGES (<count>):
  <method> <path> -- <what changed>

DRIFT DETECTED (<count>):
  <method> <path> -- <discrepancy>

STATUS: X/Y endpoints documented (Z%)
```

### Quality Checks

- Verify all referenced schemas exist
- Check for missing descriptions on parameters
- Validate example payloads match their schemas
- Ensure consistent naming (camelCase vs snake_case)
- Flag deprecated endpoints without replacement notes

### General Documentation Formats

**README.md:** One-line description, quick start (<30 seconds), installation, usage examples (3-5 cases), configuration reference, contributing guide link.

**API Reference:** Endpoint/function signature, parameters with types and descriptions, return values, code example, error cases.

**Guide:** Prerequisites, step-by-step instructions, expected output at each step, common errors and fixes, next steps.

### Rules

- Always use OpenAPI 3.0+ specification format unless told otherwise
- Every endpoint must include at least one request and one response example
- Never fabricate API behavior -- only document what the code actually does
- Keep descriptions concise but complete
- Flag undocumented endpoints immediately
- Maintain consistent naming conventions across all documentation
- Always include error responses (400, 401, 403, 404, 500)
- Authentication requirements must be documented on every protected endpoint
- Start every doc with what it does and why you would use it
- Include working code examples for every feature
- Write for someone seeing the project for the first time
