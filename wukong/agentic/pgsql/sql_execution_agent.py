# agents/sql_executor_agent.py

import json
from typing import Dict, Any, Optional
from .pg_client import PostgreSQLClient


class SQLExecutorAgent:
    def __init__(self, pgclient:PostgreSQLClient):
        self.pgclient = pgclient
        
        
    def execute_query(self, sql: str) -> Dict[str, Any]:
        connection = self.pgclient.get_connection()
        try:            
            cursor = connection.cursor()
            cursor.execute(sql)
            
            if cursor.description:
                columns = [desc[0] for desc in cursor.description]
                rows = cursor.fetchall()
                if not rows:
                    return {
                        "success": False,
                        "error": "Query returned no results",
                        "error_type": "EmptyResultError"
                    }
                result = {
                    "success": True,
                    "columns": columns,
                    "rows": [dict(zip(columns, row)) for row in rows],
                    "row_count": len(rows)
                }
            else:
                result = {
                    "success": True,
                    "message": "Query executed successfully",
                    "rows_affected": cursor.rowcount
                }
            
            cursor.close()
            return result
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__
            }
        finally:
            if connection:
                self.pgclient.release_connection(connection)
                
                

    def execute_and_validate(self, sql: str) -> Dict[str, Any]:
        result = self.execute_query(sql)
        return self._format_result(sql, result)

    
    def _format_result(self, sql: str, execution_result: Dict[str, Any]) -> Dict[str, Any]:
        if execution_result["success"]:
            return {
                "success": True,
                "sql": sql,
                "data": execution_result.get("rows", []),
                "columns": execution_result.get("columns", []),
                "row_count": execution_result.get("row_count", 0),
                "message": "Query executed successfully"
            }
        else:
            return {
                "success": False,
                "sql": sql,
                "error": execution_result["error"],
                "error_type": execution_result["error_type"],
                "message": "Query execution failed"
            }

    def get_feedback_for_llm(self, result: Dict[str, Any]) -> str:
        if result["success"]:
            return json.dumps({
                "status": "success",
                "row_count": result["row_count"],
                "columns": result["columns"]
            }, indent=2)
        else:
            return json.dumps({
                "status": "error",
                "error_type": result["error_type"],
                "error_message": result["error"]
            }, indent=2)