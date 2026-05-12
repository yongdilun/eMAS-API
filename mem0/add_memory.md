> ## Documentation Index
> Fetch the complete documentation index at: https://docs.mem0.ai/llms.txt
> Use this file to discover all available pages before exploring further.

# Add Memories

> Add facts, messages, or metadata to a user memory store with async processing and event tracking via the V3 additive pipeline.

Extract and store memories from a conversation using the V3 additive pipeline. The endpoint uses single-pass ADD-only extraction — one LLM call, no UPDATE/DELETE. Memories accumulate over time; nothing is overwritten.

## Endpoint

* **Method**: `POST`
* **URL**: `/v3/memories/add/`
* **Content-Type**: `application/json`

Processing is asynchronous. The response returns an `event_id` you can poll via `GET /v1/event/{event_id}/`.

## Required headers

| Header                                | Required | Description                       |
| ------------------------------------- | -------- | --------------------------------- |
| `Authorization: Token <MEM0_API_KEY>` | Yes      | API key scoped to your workspace. |
| `Accept: application/json`            | Yes      | Ensures a JSON response.          |

## Request body

Provide conversation messages for Mem0 to extract memories from. At least one entity ID (`user_id`, `agent_id`, `app_id`, or `run_id`) is required so the memory is scoped to a session. Entity IDs are accepted at the top level.

<CodeGroup>
  ```json Basic request theme={null}
  {
    "user_id": "alice",
    "messages": [
      { "role": "user", "content": "I moved to Austin last month." }
    ],
    "metadata": {
      "source": "onboarding_form"
    }
  }
  ```
</CodeGroup>

### Common fields

| Field      | Type                     | Required | Description                                                                                            |
| ---------- | ------------------------ | -------- | ------------------------------------------------------------------------------------------------------ |
| `messages` | array                    | Yes      | Conversation turns for Mem0 to extract memories from. Each object should include `role` and `content`. |
| `user_id`  | string                   | No\*     | Associates the memory with a user.                                                                     |
| `agent_id` | string                   | No\*     | Associates the memory with an agent.                                                                   |
| `run_id`   | string                   | No\*     | Associates the memory with a run.                                                                      |
| `app_id`   | string                   | No\*     | Associates the memory with an app.                                                                     |
| `metadata` | object                   | Optional | Custom key/value metadata (e.g., `{"topic": "preferences"}`).                                          |
| `infer`    | boolean (default `true`) | Optional | Set to `false` to skip inference and store the provided text as-is.                                    |

> \* At least one entity ID (`user_id`, `agent_id`, `app_id`, or `run_id`) is required.

<Tip>
  Need more details? See [all request parameters](#body-messages) below for complete field descriptions, types, and constraints.
</Tip>

## Response

The request is queued for background processing. The response contains an `event_id` for tracking status.

<CodeGroup>
  ```json 200 response theme={null}
  {
    "message": "Memory processing has been queued for background execution",
    "status": "PENDING",
    "event_id": "evt-uuid"
  }
  ```

  ```json 400 response theme={null}
  {
    "error": "400 Bad Request",
    "details": {
      "message": "Invalid input data. Please refer to the memory creation documentation at https://docs.mem0.ai/platform/quickstart#4-1-create-memories for correct formatting and required fields."
    }
  }
  ```
</CodeGroup>

<Info>
  Poll the event status via `GET /v1/event/{event_id}/`. Status will be `SUCCEEDED` or `FAILED` once processing completes.
</Info>


## OpenAPI

````yaml post /v3/memories/add/
openapi: 3.0.1
info:
  title: Mem0 API Docs
  description: mem0.ai API Docs
  contact:
    email: support@mem0.ai
  license:
    name: Apache 2.0
  version: v1
servers:
  - url: https://api.mem0.ai/
security:
  - ApiKeyAuth: []
paths:
  /v3/memories/add/:
    post:
      tags:
        - memories
      summary: Add memories (V3)
      description: >-
        Extract and store memories from a conversation using the V3 additive
        pipeline. Entity IDs (`user_id` / `agent_id` / `run_id`) are accepted at
        the top level. At least one entity ID is required so the memory is
        scoped to a session.
      operationId: memories_add_v3
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required:
                - messages
              properties:
                messages:
                  type: array
                  description: Conversation messages to extract memories from.
                  items:
                    type: object
                    properties:
                      role:
                        type: string
                        enum:
                          - user
                          - assistant
                          - system
                      content:
                        type: string
                    required:
                      - role
                      - content
                user_id:
                  type: string
                  description: Scope memories to this user.
                agent_id:
                  type: string
                  description: Scope memories to this agent.
                run_id:
                  type: string
                  description: Scope memories to this session / run.
                metadata:
                  type: object
                  additionalProperties: true
                  description: User-supplied metadata to attach to each extracted memory.
                custom_instructions:
                  type: string
                  description: >-
                    Project-level instructions that guide extraction for this
                    call.
                infer:
                  type: boolean
                  default: true
                  description: >-
                    When `false`, stores each message verbatim without running
                    the extraction LLM.
            example:
              messages:
                - role: user
                  content: I just moved to San Francisco from New York.
                - role: assistant
                  content: Got it — I'll update your location.
              user_id: alice
      responses:
        '200':
          description: >-
            Memory addition queued; returns an event identifier clients can poll
            via `GET /v1/event/{event_id}/`.
          content:
            application/json:
              schema:
                type: object
                properties:
                  message:
                    type: string
                  status:
                    type: string
                    enum:
                      - PENDING
                      - SUCCEEDED
                      - FAILED
                  event_id:
                    type: string
                    format: uuid
              example:
                message: Memory processing has been queued for background execution
                status: PENDING
                event_id: 2c4d1f44-4f7b-4b2f-9f6e-7b5b4f5a1234
        '400':
          description: Validation error — e.g. missing `messages` or no entity ID supplied.
        '401':
          description: Unauthorized — missing or invalid API key.
      security:
        - tokenAuth: []
      x-codeSamples:
        - lang: cURL
          source: |-
            curl -X POST https://api.mem0.ai/v3/memories/add/ \
              -H "Authorization: Token <api-key>" \
              -H "Content-Type: application/json" \
              -d '{
                "messages": [
                  {"role": "user", "content": "I just moved to San Francisco from New York."},
                  {"role": "assistant", "content": "Got it — I\u0027ll update your location."}
                ],
                "user_id": "alice"
              }'
        - lang: Python
          source: |-
            from mem0 import MemoryClient

            client = MemoryClient(api_key="your-api-key")

            result = client.add(
                messages=[
                    {"role": "user", "content": "I just moved to San Francisco from New York."},
                    {"role": "assistant", "content": "Got it — I'll update your location."}
                ],
                user_id="alice",
            )
            print(result)
        - lang: JavaScript
          source: |-
            import MemoryClient from "mem0ai";

            const client = new MemoryClient({ apiKey: "your-api-key" });

            const result = await client.add(
              [
                { role: "user", content: "I just moved to San Francisco from New York." },
                { role: "assistant", content: "Got it — I'll update your location." },
              ],
              { userId: "alice" }
            );
            console.log(result);
components:
  securitySchemes:
    ApiKeyAuth:
      type: apiKey
      in: header
      name: Authorization
      description: >-
        API key authentication. Prefix your Mem0 API key with 'Token '. Example:
        'Token your_api_key'

````