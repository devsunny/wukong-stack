from pathlib import Path
from typing import Dict, Optional, Union


class SQLPromptBuilder:
    def __init__(self, schema_context:Union[Path, str], schema_reload:bool=False   ):
        self.schema_context = schema_context.read_text() if isinstance(schema_context, Path) else schema_context
        self.schema_reload = schema_reload

    def build_initial_prompt(self, user_query: str) -> str:
        if self.schema_reload and isinstance(self.schema_context, Path):
            self.schema_context = self.schema_context.read_text()
        prompt = f"""You are an expert SQL query generator for PostgreSQL databases.

{self.schema_context}

IMPORTANT INSTRUCTIONS:
1. Generate ONLY valid PostgreSQL SQL queries
2. Use proper schema.table notation when querying across multiple schemas
3. Consider the column descriptions and value mappings provided above
4. When matching text values, account for alternative forms (e.g., 'Japan' vs 'JPN')
5. Use ILIKE for case-insensitive string matching when appropriate
6. Return ONLY the SQL query without any explanations or markdown formatting
7. Do not include semicolons at the end
8. Ensure the query is properly formatted and executable
9. Only produce SELECT/CTE/EXPLAIN queries. No DML/DDL
10. Prefer schema-qualified table names when helpful

USER QUERY: {user_query}

Generate the SQL query:"""
        return prompt

    def build_fix_prompt(
        self,
        user_query: str,
        failed_sql: str,
        error_message: str,
        attempt: int
    ) -> str:
        if self.schema_reload and isinstance(self.schema_context, Path):
            self.schema_context = self.schema_context.read_text()
        
        prompt = f"""The previous SQL query failed to execute. Please fix it.

{self.schema_context}

ORIGINAL USER QUERY: {user_query}

FAILED SQL QUERY:
{failed_sql}

ERROR MESSAGE:
{error_message}

ATTEMPT: {attempt}

INSTRUCTIONS:
1. Analyze the error message carefully
2. Fix the SQL query to resolve the error
3. Ensure proper table and column names are used
4. Check for syntax errors, missing joins, or incorrect references
5. Return ONLY the corrected SQL query without explanations or markdown
6. Do not include semicolons at the end

Generate the corrected SQL query:"""
        return prompt