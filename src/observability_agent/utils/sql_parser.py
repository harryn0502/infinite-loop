"""SQL parsing utilities."""

import re


def extract_sql_from_text(text: str) -> str:
    """
    Extract SQL query from LLM output.

    Looks for SQL code blocks in the format ```sql ... ```
    and extracts the query. If no code block is found,
    returns the entire text.

    Args:
        text: LLM response text potentially containing SQL

    Returns:
        Extracted SQL query string
    """
    # ```sql ... ``` 패턴 찾기
    pattern = r"```sql(.*?)```"
    match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
    if match:
        sql = match.group(1).strip()
        return sql
    return text.strip()
