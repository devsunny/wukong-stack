import psycopg2
import psycopg2.pool
import json
from io import StringIO
from wukong.utils  import CustomJsonEncoder
import re
from typing import List, Dict, Any, Optional, Tuple
import logging
from urllib.parse import urlparse

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from wukong.utils import json_utils
from .pg_prompts import TABLE_DESCRIPTION_PROMPT, COLUMN_DESCRITOPN_PROMPT


class PostgreSQLClient:
    """
    A PostgreSQL client class for managing database connections and executing queries.
    Supports both individual connection parameters and database URL.
    Context manager compatible for automatic resource cleanup.
    """
    
    def __init__(self, host: Optional[str] = None, port: Optional[int] = None, 
                 database: Optional[str] = None, user: Optional[str] = None, 
                 password: Optional[str] = None, database_url: Optional[str] = None,
                 min_conn: int = 1, max_conn: int = 10):
        """
        Initialize PostgreSQL client with connection parameters or database URL.
        
        Args:
            host: Database host address
            port: Database port number
            database: Database name
            user: Database user
            password: Database password
            database_url: Database URL (e.g., postgresql://user:password@host:port/database)
            min_conn: Minimum number of connections in pool
            max_conn: Maximum number of connections in pool
            
        Note:
            If database_url is provided, it takes precedence over individual parameters.
        """
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Initialize Rich console
        self.console = Console()
        
        # Parse connection parameters
        if database_url:
            self._parse_database_url(database_url)
        elif all([host, database, user, password]):
            self.host = host
            self.port = port or 5432
            self.database = database
            self.user = user
            self.password = password
        else:
            raise ValueError(
                "Either provide database_url or all of (host, database, user, password)"
            )
        
        self.min_conn = min_conn
        self.max_conn = max_conn
        self.connection_pool = None
        self.llm_client = None
        # Initialize connection pool
        self._initialize_pool()
    
    def _initialize_pool(self):
        """Initialize the connection pool."""
        try:
            self.connection_pool = psycopg2.pool.SimpleConnectionPool(
                self.min_conn,
                self.max_conn,
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password
            )
            self.logger.info("Connection pool created successfully")
        except Exception as e:
            self.logger.error(f"Error creating connection pool: {e}")
            raise
    
    
    def get_tables(self, schema: str) -> List[str]:
        """
        Retrieve a list of table names in the specified schema.
        
        Args:
            schema: Schema name (e.g., 'public')   
        Returns:
            List of table names
        """
        query = """
        SELECT table_name
        FROM information_schema.tables
        WHERE lower(table_schema) = lower(%s)
        ORDER BY table_name;
        """
        try:
            results = self.execute_query(query, (schema,))
            tables = [f"{schema}.{row['table_name']}" for row in results]
            return tables
        except Exception as e:
            self.logger.error(f"Error retrieving tables: {e}")
            raise
    
    
    def _parse_database_url(self, database_url: str):
        """
        Parse database URL and extract connection parameters.
        
        Args:
            database_url: Database URL string
            
        Supported formats:
            - postgresql://user:password@host:port/database
            - postgres://user:password@host:port/database
            - postgresql://user:password@host/database (default port 5432)
        """
        try:
            parsed = urlparse(database_url)
            
            if parsed.scheme not in ['postgresql', 'postgres']:
                raise ValueError(f"Invalid database URL scheme: {parsed.scheme}")
            
            self.host = parsed.hostname
            self.port = parsed.port or 5432
            self.database = parsed.path.lstrip('/')
            self.user = parsed.username
            self.password = parsed.password
            
            # Validate required fields
            if not all([self.host, self.database, self.user]):
                raise ValueError("Database URL must contain host, database, and user")
            
            self.logger.info(f"Parsed database URL: {self.user}@{self.host}:{self.port}/{self.database}")
            
        except Exception as e:
            self.logger.error(f"Error parsing database URL: {e}")
            raise
    
    def __enter__(self):
        """
        Enter the context manager.
        
        Returns:
            Self instance
        """
        self.logger.info("Entering context manager")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Exit the context manager and cleanup resources.
        
        Args:
            exc_type: Exception type if an exception occurred
            exc_val: Exception value if an exception occurred
            exc_tb: Exception traceback if an exception occurred
            
        Returns:
            False to propagate exceptions
        """
        self.logger.info("Exiting context manager")
        self.close_all_connections()
        
        if exc_type is not None:
            self.logger.error(f"Exception occurred: {exc_type.__name__}: {exc_val}")
        
        # Return False to propagate exceptions
        return False
    
    def get_connection(self):
        """
        Get a connection from the pool.
        
        Returns:
            A database connection object
        """
        try:
            if self.connection_pool is None:
                raise RuntimeError("Connection pool is not initialized")
            
            connection = self.connection_pool.getconn()
            self.logger.info("Connection retrieved from pool")
            return connection
        except Exception as e:
            self.logger.error(f"Error getting connection: {e}")
            raise
    
    def release_connection(self, connection):
        """
        Return a connection back to the pool.
        
        Args:
            connection: The connection to release
        """
        try:
            if self.connection_pool is None:
                raise RuntimeError("Connection pool is not initialized")
            
            self.connection_pool.putconn(connection)
            self.logger.info("Connection returned to pool")
        except Exception as e:
            self.logger.error(f"Error releasing connection: {e}")
            raise
    
    def execute_query(self, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """
        Execute a SELECT query and return results.
        
        Args:
            query: SQL query string
            params: Query parameters (optional)
            
        Returns:
            List of dictionaries containing query results
        """
        connection = None
        cursor = None
        
        try:
            connection = self.get_connection()
            cursor = connection.cursor()
            
            if params:
                self.logger.info(f"Executing query: {query} with params {params}")
                cursor.execute(query, params)
            else:
                self.logger.info(f"Executing query: {query} without params")
                cursor.execute(query)
            
            # Fetch column names
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            
            # Fetch all results
            results = cursor.fetchall()
            
            # Convert to list of dictionaries
            result_list = [dict(zip(columns, row)) for row in results]
            
            self.logger.info(f"Query executed successfully. Rows returned: {len(result_list)}")
            return result_list
            
        except Exception as e:
            self.logger.error(f"Error executing query: {e}")
            raise
        finally:
            if cursor:
                cursor.close()
            if connection:
                self.release_connection(connection)
    
    def execute_update(self, query: str, params: Optional[tuple] = None) -> int:
        """
        Execute an INSERT, UPDATE, or DELETE query.
        
        Args:
            query: SQL query string
            params: Query parameters (optional)
            
        Returns:
            Number of rows affected
        """
        connection = None
        cursor = None
        
        try:
            connection = self.get_connection()
            cursor = connection.cursor()
            
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            connection.commit()
            rows_affected = cursor.rowcount
            
            self.logger.info(f"Update executed successfully. Rows affected: {rows_affected}")
            return rows_affected
            
        except Exception as e:
            if connection:
                connection.rollback()
            self.logger.error(f"Error executing update: {e}")
            raise
        finally:
            if cursor:
                cursor.close()
            if connection:
                self.release_connection(connection)
    
    def execute_many(self, query: str, params_list: List[tuple]) -> int:
        """
        Execute a query multiple times with different parameters.
        
        Args:
            query: SQL query string
            params_list: List of parameter tuples
            
        Returns:
            Number of rows affected
        """
        connection = None
        cursor = None
        
        try:
            connection = self.get_connection()
            cursor = connection.cursor()
            
            cursor.executemany(query, params_list)
            connection.commit()
            rows_affected = cursor.rowcount
            
            self.logger.info(f"Batch execution successful. Rows affected: {rows_affected}")
            return rows_affected
            
        except Exception as e:
            if connection:
                connection.rollback()
            self.logger.error(f"Error executing batch: {e}")
            raise
        finally:
            if cursor:
                cursor.close()
            if connection:
                self.release_connection(connection)
    
    def _split_sql_statements(self, sql_script: str) -> List[str]:
        """
        Split SQL script into individual statements.
        
        Args:
            sql_script: SQL script containing multiple statements
            
        Returns:
            List of individual SQL statements
        """
        # Remove comments
        sql_script = re.sub(r'--.*$', '', sql_script, flags=re.MULTILINE)
        sql_script = re.sub(r'/\*.*?\*/', '', sql_script, flags=re.DOTALL)
        
        # Split by semicolon but preserve semicolons in strings
        statements = []
        current_statement = []
        in_string = False
        escape_next = False
        
        for i, char in enumerate(sql_script):
            if escape_next:
                current_statement.append(char)
                escape_next = False
                continue
            
            if char == '\\':
                escape_next = True
                current_statement.append(char)
                continue
            
            if char == "'" and not in_string:
                in_string = True
                current_statement.append(char)
            elif char == "'" and in_string:
                in_string = False
                current_statement.append(char)
            elif char == ';' and not in_string:
                stmt = ''.join(current_statement).strip()
                if stmt:
                    statements.append(stmt)
                current_statement = []
            else:
                current_statement.append(char)
        
        # Add last statement if exists
        stmt = ''.join(current_statement).strip()
        if stmt:
            statements.append(stmt)
        
        return statements
    
    def _is_select_query(self, sql: str) -> bool:
        """Check if SQL statement is a SELECT query."""
        sql_upper = sql.strip().upper()
        return sql_upper.startswith('SELECT') or sql_upper.startswith('WITH')
    
    def _is_ddl_query(self, sql: str) -> bool:
        """Check if SQL statement is a DDL query."""
        sql_upper = sql.strip().upper()
        ddl_keywords = ['CREATE', 'ALTER', 'DROP', 'TRUNCATE', 'RENAME']
        return any(sql_upper.startswith(keyword) for keyword in ddl_keywords)
    
    def _display_table(self, results: List[Dict[str, Any]], title: str = "Query Results"):
        """
        Display query results as a Rich table.
        
        Args:
            results: List of dictionaries containing query results
            title: Title for the table
        """
        if not results:
            self.console.print(Panel(f"[yellow]No results returned[/yellow]", title=title))
            return
        
        # Create Rich table
        table = Table(title=title, show_header=True, header_style="bold magenta")
        
        # Add columns
        columns = list(results[0].keys())
        for col in columns:
            table.add_column(col, style="cyan")
        
        # Add rows
        for row in results:
            table.add_row(*[str(value) if value is not None else "NULL" for value in row.values()])
        
        self.console.print(table)
        self.console.print(f"[green]Total rows: {len(results)}[/green]\n")
    
    def execute_sql_script(self, sql_script: str, display_results: bool = True) -> Dict[str, Any]:
        """
        Execute a SQL script containing multiple statements.
        For SELECT queries, display results in a Rich table.
        For DML/DDL queries, display affected rows.
        
        Args:
            sql_script: SQL script string containing one or more statements
            display_results: Whether to display results using Rich console
            
        Returns:
            Dictionary containing execution summary
        """
        connection = None
        cursor = None
        summary = {
            'total_statements': 0,
            'successful': 0,
            'failed': 0,
            'results': []
        }
        
        try:
            connection = self.get_connection()
            cursor = connection.cursor()
            
            # Split script into individual statements
            statements = self._split_sql_statements(sql_script)
            summary['total_statements'] = len(statements)
            
            if display_results:
                self.console.print(Panel(
                    f"[bold blue]Executing SQL Script[/bold blue]\n"
                    f"Total statements: {len(statements)}",
                    title="SQL Script Execution"
                ))
            
            for idx, statement in enumerate(statements, 1):
                try:
                    if display_results:
                        self.console.print(f"\n[bold]Statement {idx}:[/bold]")
                        self.console.print(Panel(statement, border_style="blue"))
                    
                    cursor.execute(statement)
                    
                    # Check if it's a SELECT query
                    if self._is_select_query(statement):
                        # Fetch results
                        columns = [desc[0] for desc in cursor.description] if cursor.description else []
                        results = cursor.fetchall()
                        result_list = [dict(zip(columns, row)) for row in results]
                        
                        if display_results:
                            self._display_table(result_list, f"Results - Statement {idx}")
                        
                        summary['results'].append({
                            'statement_number': idx,
                            'type': 'SELECT',
                            'statement': statement,
                            'rows_returned': len(result_list),
                            'data': result_list
                        })
                    
                    else:
                        # DML or DDL query
                        connection.commit()
                        rows_affected = cursor.rowcount
                        
                        query_type = 'DDL' if self._is_ddl_query(statement) else 'DML'
                        
                        if display_results:
                            if rows_affected >= 0:
                                self.console.print(
                                    f"[green]✓ {query_type} executed successfully. "
                                    f"Rows affected: {rows_affected}[/green]\n"
                                )
                            else:
                                self.console.print(
                                    f"[green]✓ {query_type} executed successfully.[/green]\n"
                                )
                        
                        summary['results'].append({
                            'statement_number': idx,
                            'type': query_type,
                            'statement': statement,
                            'rows_affected': rows_affected if rows_affected >= 0 else 0
                        })
                    
                    summary['successful'] += 1
                    
                except Exception as e:
                    connection.rollback()
                    summary['failed'] += 1
                    error_msg = str(e)
                    
                    if display_results:
                        self.console.print(f"[red]✗ Error executing statement {idx}:[/red]")
                        self.console.print(f"[red]{error_msg}[/red]\n")
                    
                    summary['results'].append({
                        'statement_number': idx,
                        'type': 'ERROR',
                        'statement': statement,
                        'error': error_msg
                    })
                    
                    self.logger.error(f"Error in statement {idx}: {error_msg}")
            
            # Display summary
            if display_results:
                summary_text = Text()
                summary_text.append("Execution Summary\n", style="bold")
                summary_text.append(f"Total Statements: {summary['total_statements']}\n")
                summary_text.append(f"Successful: {summary['successful']}\n", style="green")
                if summary['failed'] > 0:
                    summary_text.append(f"Failed: {summary['failed']}\n", style="red")
                
                self.console.print(Panel(summary_text, title="Summary", border_style="green"))
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Error executing SQL script: {e}")
            raise
        finally:
            if cursor:
                cursor.close()
            if connection:
                self.release_connection(connection)
    
    def execute_sql_file(self, file_path: str, display_results: bool = True) -> Dict[str, Any]:
        """
        Execute SQL statements from a file.
        
        Args:
            file_path: Path to SQL file
            display_results: Whether to display results using Rich console
            
        Returns:
            Dictionary containing execution summary
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                sql_script = f.read()
            
            if display_results:
                self.console.print(f"[bold blue]Reading SQL file: {file_path}[/bold blue]\n")
            
            return self.execute_sql_script(sql_script, display_results)
            
        except FileNotFoundError:
            error_msg = f"SQL file not found: {file_path}"
            self.logger.error(error_msg)
            raise FileNotFoundError(error_msg)
        except Exception as e:
            self.logger.error(f"Error reading SQL file: {e}")
            raise
    
    def get_table_foreign_keys(self, table_name: str) -> List[Dict]:    
        """
        Retrieve foreign key constraints for a specified table.
        
        Args:
            table_name: Name of the table   
            
        Returns:
            List of foreign key constraints
        """
        
        query = """
        SELECT
            kcu.column_name,
            ccu.table_name AS foreign_table_name,
            ccu.column_name AS foreign_column_name,
            rc.update_rule AS on_update,
            rc.delete_rule AS on_delete
        FROM 
            information_schema.table_constraints AS tc
            JOIN information_schema.key_column_usage AS kcu
              ON tc.constraint_name = kcu.constraint_name
              AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage AS ccu
              ON ccu.constraint_name = tc.constraint_name
              AND ccu.table_schema = tc.table_schema
            JOIN information_schema.referential_constraints AS rc
              ON tc.constraint_name = rc.constraint_name
              AND tc.table_schema = rc.constraint_schema
        WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_schema = lower(%s) AND tc.table_name = lower(%s);
        """
        schema = "public"  # default schema
        if '.' in table_name:
            schema, table_name = table_name.split('.', 1)
        
        try:
            results = self.execute_query(query, (schema, table_name,))
            return results
            
        except Exception as e:
            self.logger.error(f"Error retrieving foreign keys for table '{table_name}': {e}")
            raise   
        
    
    def get_table_primary_key(self, table_name: str) -> List[str]:
        """
        Retrieve the primary key column of a specified table.
        
        Args:
            table_name: Name of the table
            
        Returns:
            Primary key column name or None if no primary key exists
        """
        query = """
        SELECT
        kcu.column_name
        FROM
            information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
            ON tc.constraint_name = kcu.constraint_name
            AND tc.table_schema = kcu.table_schema
        WHERE
            tc.constraint_type = 'PRIMARY KEY'            
            AND tc.table_schema = lower(%s)
            AND tc.table_name =lower(%s)
        """ 
        schema = "public"  # default schema
        if '.' in table_name:
            schema, table_name = table_name.split('.', 1)
        pks = []    
        try:
            results = self.execute_query(query, (schema, table_name,))
            for row in results: 
                pks.append(row['column_name'])            
            return pks
        except Exception as e:
            self.logger.error(f"Error retrieving primary key for table '{table_name}': {e}")
            raise
    
        
    def get_table_schema(self, table_name: str, enhanced:bool = False) -> Optional[str]:
        """
        Retrieve the schema of a specified table.
        
        Args:
            table_name: Name of the table
            
        Returns:
            Table schema as a string or None if table does not exist
        """
        query = f"""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE  table_schema = lower(%s) and table_name = lower(%s)
        ORDER BY ordinal_position;
        """
        schema = "public"  # default schema
        if '.' in table_name:
            schema, table_name = table_name.split('.', 1)
        user_queries = []
        try:
            pks = self.get_table_primary_key(f"{schema}.{table_name}")
            fks = self.get_table_foreign_keys(f"{schema}.{table_name}")
            fks_map = {fk["column_name"]:fk for fk in fks}
                        
            results = self.execute_query(query, (schema, table_name,))
            if not results:
                self.logger.warning(f"Table '{table_name}' does not exist or has no columns.")
                return None
                        
            schema_lines = [f"Schema: {schema}", f"Table: {table_name}","Columns:"]  
            select_columns = []
                        
            for row in results:
                column = row['column_name']                
                col_type = row['data_type']  
                select_columns.append((column, col_type))
                key_tag = " "
                if row['column_name'] in pks:
                    key_tag += " [Primary Key]"
                if row['column_name'] in fks_map:
                    fk = fks_map[row['column_name']]
                    key_tag += f" [Foreign Key -> {fk['foreign_table_name']}({fk['foreign_column_name']})]"                
                
                schema_lines.append(f" - {column}: {col_type}{key_tag}")
                
                      
            try:
                descriptions = self.get_column_descriptions(schema, table_name, select_columns)
                if descriptions:                    
                    table_mds = schema_lines + ["\n**Column Metadata:**"] + descriptions
                    tb_desc_prompt = TABLE_DESCRIPTION_PROMPT.format(table_info="\n".join(table_mds))
                    resp_str = ""
                    for chunk in self.llm_client.invoke_model_stream(prompt=tb_desc_prompt):
                        resp_str += chunk
                        print(chunk, end='', flush=True)
                    print("\n")
                    resp_str = resp_str.split("</think>")[-1].strip()                    
                    try:
                        json_text = json_utils.extract_json_from_text(resp_str)                        
                        table_metadata = json.loads(json_text)
                        if 'table_description' in table_metadata:
                            schema_lines.append(f"\n**Table Description:** {table_metadata['table_description']}")                        
                        if 'example_user_queries' in table_metadata:
                            user_queries = table_metadata['example_user_queries']
                                
                    except json.JSONDecodeError as e:
                        self.logger.error(f"Error parsing table metadata JSON: {e}")
                        # Fallback to raw descriptions
                    
                    if enhanced is True:   
                        schema_lines.append("\n **Column Metadata:**")
                        schema_lines.extend(descriptions)            
            
            except Exception as e:
                self.logger.error(f"Error enhancing schema for table '{table_name}': {e}")
                
            schema_str = "\n".join(schema_lines)
            return schema_str, user_queries
            
        except Exception as e:
            self.logger.error(f"Error retrieving schema for table '{table_name}': {e}")
            raise
    
    def get_columns_data_type(self, schema: str, table_name:str, columns:List[str]) -> List[Tuple[str, str]] :
        """
        Retrieve data types for specified columns in a table.
           
        Args:
            schema: Schema name
            table_name: Table name
            columns: List of column names   
        Returns:    
            List of tuples (column_name, data_type)                 
        """
        query = f"""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE  table_schema = %s and table_name = %s and column_name = ANY(%s)
        ORDER BY ordinal_position;
        """
        try:
            results = self.execute_query(query, (schema, table_name, columns,))
            return [ (row['column_name'], row['data_type']) for row in results ]
        except Exception as e:
            self.logger.error(f"Error retrieving data types for columns in table '{table_name}': {e}")
            raise   
         
         
    
    def split_column_infos(self, column_infos:List[List[Tuple[str, str]]], limit:int = 15) -> List[List[Tuple[str, str]]]:
        """
        Split column info list into chunks of specified size.
        
        Args:
            column_infos: List of column info tuples (column_name, data_type)
            limit: Maximum number of columns per chunk
            
        Returns:
            List of column info chunks
        """
        chunks = []
        for i in range(0, len(column_infos), limit):
            chunks.append(column_infos[i:i + limit])
        return chunks   
        
    
    
    
    def get_column_descriptions(self, schema: str, table_name:str, select_columns:List[str]) -> List[str] :
        """
        Retrieve column descriptions from pg_description for specified columns.
        
        Args:
            schema: Schema name
            table_name: Table name
            select_columns: List of column names    
        Returns:
            List of column descriptions
        """
        if not select_columns:
            return []        
        assert re.search(r'^[a-zA-Z_][a-zA-Z0-9_]*$', table_name), f"Invalid table name: {table_name}"
        assert re.search(r'^[a-zA-Z_][a-zA-Z0-9_]*$', schema), f"Invalid schema name: {schema}"
        descriptions = []
        try:
            for column_chunks in self.split_column_infos(select_columns, limit=15):
                columns_info = []
                for column, col_type in column_chunks:
                    assert re.search(r'^[a-zA-Z_][a-zA-Z0-9_]*$', column), f"Invalid column name: {column}"
                    
                    data_query = f"""select "{column}" from (
                        select "{column}", random() as rand from (
                        select distinct "{column}" from {schema}.{table_name} where "{column}" is not null
                        ) c order by rand limit 100
                        ) r"""
                    
                    
                    try:
                        results = self.execute_query(data_query)  
                        sample_values = json.dumps( [ row[column] for row in results] , cls=CustomJsonEncoder) 
                    except Exception as e:
                        sample_values = "[]" 
                        
                    columns_info.append(f"- Column Name: {column}\n - Data Type: {col_type}\n - Sample Values: {sample_values}\n")
                
                columns_info_str = "\n".join(columns_info)  
                                    
                prompt = COLUMN_DESCRITOPN_PROMPT.format(column_name=column, columns_info=columns_info_str)                
                response_text = self.llm_client.invoke_model_stream(prompt=prompt, streaming_handler=lambda x: print(x, end='', flush=True))
                response_text = response_text.split("</think>")[-1].strip()
                
                print("-------------------------------\n")
                print(response_text)
                print("\n-------------------------------\n")
                clean_text = ""
                started = False
                for line in StringIO(response_text):
                    if not started and line.startswith("```"):
                        started = True                        
                    if started and line.startswith("```"):
                        started = False
                        clean_text += "\n"
                    if line:
                        clean_text += line                
                
                descriptions.append(clean_text)
                
        except Exception as e:
            self.logger.error(f"Error retrieving column descriptions for table '{table_name}': {e}")
            raise   
        return descriptions
           
    
    def close_all_connections(self):
        """
        Close all connections in the pool.
        """
        try:
            if self.connection_pool is not None:
                self.connection_pool.closeall()
                self.logger.info("All connections closed")
        except Exception as e:
            self.logger.error(f"Error closing connections: {e}")
            raise

