import pathlib
from typing import List
import click
from rich.console import Console
from .pg_client import PostgreSQLClient
from ...wukong_config import wukong_config
from wukong.llm.llm_client import LLMClient

PG_CLIENT_PARAMS = [
    "database_url", "host", "port", "database", "user", "password", "max_conn"
]

@click.group()
def pg_sql():
    """PostgreSQL database Client related commands"""
    pass


def get_pg_config(section: str) -> dict:    
    dbprop = wukong_config.get(section)
    if not dbprop:
        raise ValueError(f"{section} is not configured in .wukong.toml")
    pgprops = {k: v for k, v in dbprop.items() if k in PG_CLIENT_PARAMS}
    if 'url' in dbprop:
        database_url = dbprop['url']        
        pgprops["database_url"] = database_url
    return pgprops


def get_llm_client(self) -> LLMClient:
    llm_config = wukong_config.get("llm", {})     
    base_url = llm_config.get("base_url", None)
    api_key = llm_config.get("api_key", None)
    models = llm_config.get("model_id", {})  
    assert models is not None, "model_id must be specified in [llm] section of .wukong.toml"     
    model_id = models[0] if isinstance(models, list) else models    
    max_completion_tokens = llm_config.get("max_completion_tokens", 3200) 
    fallback_models = llm_config.get("fallback_models", [])                 
    llm_client = LLMClient(
        model_id=model_id,
        base_url=base_url,
        api_key=api_key,
        max_completion_tokens=max_completion_tokens,
        fallback_models=fallback_models, 
        streaming_handler=None
    )
    return llm_client



@click.command()
@click.option("--database", "-d", type=str, default="database", help="database configuration section name in .wukong.toml") 
@click.option("--sql-file", "-s", type=click.Path(exists=True, file_okay=True, dir_okay=False, path_type=pathlib.Path), default=None, help="Path to SQL script file")     
@click.option("--sql-string", "-q", type=str, default=None, help="SQL script string")     
def execute_sql(database: str, sql_file:pathlib.Path=None, sql_string:str=None):
    """simple postgresql client, execute DML and DDL statements"""
    console = Console()    
    dbprop = get_pg_config(database)    
    with PostgreSQLClient(**dbprop) as dbclient:    
        
        if sql_file is not None:
            console.print(f"[yellow]Excuting SQL File[/yellow] {sql_file}")
            dbclient.execute_sql_file(sql_file.resolve())
        
        if sql_string is not None:
            console.print(f"[yellow]Excuting SQL query[/yellow]")
            dbclient.execute_sql_script(sql_string)


@click.command()
@click.option("--database", "-d", type=str, default="database", help="database configuration section name in .kara_code.env.toml") 
@click.option("--schema-file", "-o", type=click.Path(exists=False, file_okay=True, dir_okay=False, path_type=pathlib.Path), default=None, help="Path to schema file output")     
@click.option("--enhance", "-e",  is_flag=True, type=bool, default=False, help="Enhance schema with column descriptions using LLM")
@click.option("--schema", "-s",  type=str, help="Schema Name", default=None)
@click.argument("tables",  type=str, nargs=-1)
def text_to_sql_schema(database: str, schema_file:pathlib.Path, tables:List[str], schema:str, enhance:bool):
    """generate LLM table schema for text to SQL"""
    assert tables or schema is not None, "Either tables or schema must be specified"
    console = Console()
    dbprop = get_pg_config(database)   
    with PostgreSQLClient(**dbprop) as dbclient: 
        dbclient.llm_client = get_llm_client(dbclient)       
        schemas = []
        if not tables:
            tables = dbclient.get_tables(schema)
            if not tables:
                console.print(f"[yellow]No tables found in schema {schema}[/yellow]")
                return
        
        for table in tables:
            db_schema  = dbclient.get_table_schema(table, enhance)
            if db_schema is None:
                console.print(f"[yellow]No such table {table}[/yellow]")
            else:
                schemas.append(db_schema)
        
        if schema_file is not None:
            schema_file.write_text("\n\n".join(schemas), encoding="utf-8")
            console.print(f"[green]✔ Schema is written to {schema_file}[/green]")
        else:
            console.print("\n\n".join(schemas)) 
            

@click.command()
@click.option("--database", "-d", type=str, default="database", help="database configuration section name in .kara_code.env.toml") 
@click.option("--schema", "-s", type=str, help="schema name", default="public")     
@click.option("--table", "-t",  type=str, help="table name", required=True)
@click.argument("columns",  type=str, nargs=-1, required=True)
def describe_columns(database: str, schema:str, table:str, columns:bool):
    """enahnce column metadata with descriptions using LLM for text to SQL"""    
    console = Console()
    dbprop = get_pg_config(database)   
    with PostgreSQLClient(**dbprop) as dbclient:        
        dbclient.llm_client = get_llm_client(dbclient)
        cols =dbclient.get_columns_data_type(schema, table, list(columns))
        descriptions = dbclient.get_column_descriptions(schema, table, cols)
        if not descriptions:
            console.print(f"[yellow]No descriptions found for {table}({', '.join(columns)})[/yellow]")
            return
                
    console.print("\n\n".join(descriptions))
    

@click.command()
@click.option("--database", "-d", type=str, default="database", help="database configuration section name in .kara_code.env.toml") 
@click.option("--schema-file", "-s", type=click.Path(exists=True, file_okay=True, dir_okay=False, path_type=pathlib.Path), help="Path to schema file for text to SQL", required=True)  
@click.option("--reload", "-r",  is_flag=True, type=bool, default=False, help="Reload schema from file every time")  
def text_to_sql_chat(database: str, schema_file:pathlib.Path, reload:bool):
    """Start an interactive chat session to interact with PostgreSQL database using LLM powered text to SQL"""
    from .pg_agent_shell import PgAgentShell
    dbprop = get_pg_config(database)   
    with PostgreSQLClient(**dbprop) as dbclient:   
        shell = PgAgentShell(schema_file, dbclient, wukong_config, reload)
        shell.run()
                

pg_sql.add_command(execute_sql, "execute")
pg_sql.add_command(text_to_sql_schema, "llm-schema")
pg_sql.add_command(describe_columns, "describe_columns")
pg_sql.add_command(text_to_sql_chat, "chat")