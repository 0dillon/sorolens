with open('docs/openapi.yaml', 'r', encoding='utf-8') as f:
    content = f.read()

route = """  /api/v1/watchdog/subscriptions/{id}/deliveries:
    get:
      summary: List webhook deliveries for a subscription
      tags: [Watchdog]
      parameters:
        - name: id
          in: path
          required: true
          schema:
            type: string
      responses:
        '200':
          description: OK

components:"""

content = content.replace("components:", route, 1)

with open('docs/openapi.yaml', 'w', encoding='utf-8') as f:
    f.write(content)
