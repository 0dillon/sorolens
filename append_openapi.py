with open('docs/openapi.yaml', 'a', encoding='utf-8') as f:
    f.write("""
  /api/v1/watchdog/subscriptions/{id}/deliveries:
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
""")
