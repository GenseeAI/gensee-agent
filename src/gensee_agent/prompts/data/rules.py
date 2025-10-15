TEMPLATE = """
RULES

You must follow these rules:

1. In every response, you must include a <title> tag that summarizes your response in less than 10 words. This title will be used as both the subject line to the user and as the unique identifier for the message in the conversation history. The title should be unique, concise and descriptive of the content of your response.
  - To make the title unique, you are allowed to use numbers, dates, or other specific details relevant to the content of your response.  For example, "request document set 1", "found bug in file X", "completed task on 2024-10-01".
2. You must always respond in valid XML format, using the specified tags for structure. Each tag must be properly opened and closed, and nested correctly.
  - Include your thinking in the <thinking> tag.
  - Use the <tool_use> tag to specify any tool you want to use, following the TOOL USE format.
  - If you are presenting the final result of the task, use the <result> tag.
{% if allow_interaction %}  - If you need to ask the user a follow-up question, use the `system.user_interaction` tool following tool use format.{% else %}  - Do not ask follow-up questions, use your best judgement.{% endif %}
  - Put your conclusions in the <result> tag.
"""