# llm_chat_history_manager.py
# Requires: json, os, pathlib, datetime

import json
import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Any


class LLMHistoryManager:
    """
    Manages LLM history with persistent storage in JSON format.
    
    This class handles saving, loading, and managing chat history for LLM interactions,
    storing the data in a JSON file located at $HOME/.phanes/.llm_message_history.
    
    Attributes:
        max_history (int): Maximum number of history entries to keep.
        history_file_path (Path): Path to the history file.
        history (List[Dict[str, Any]]): In-memory list of chat history entries.
    """
    
    def __init__(self, max_history: int = 200):
        """
        Initialize the LLM Chat History Manager.
        
        Args:
            max_history (int): Maximum number of history entries to keep. Defaults to 100.
        """
        self.max_history = max_history
        self.history_file_path = Path.home() / '.wukong' / '.llm_history'
        self.history: List[Dict[str, Any]] = []
        self._ensure_directory_exists()
        self.load_history()
        
    def add_user_message(self, message: str) -> None:
        """
        Add a user message to the history.
        
        Args:
            message (str): The user message to add.
        """
        entry = {
            'timestamp': datetime.now().isoformat(),
            "message":{'role': 'user',
            'content': message}
        }
        self.history.append(entry)
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]
        self.save_history()
        
    def add_assistant_message(self, message: str) -> None:
        """
        Add an assistant message to the history.
        
        Args:
            message (str): The assistant message to add.
        """
        entry = {
            'timestamp': datetime.now().isoformat(),
            "message":{'role': 'assistant',
            'content': message}
        }
        self.history.append(entry)
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]
        self.save_history()
    
    def _ensure_directory_exists(self) -> None:
        """
        Ensure the directory for the history file exists.
        
        Creates the .phanes directory in the user's home directory if it doesn't exist.
        """
        directory = self.history_file_path.parent
        directory.mkdir(parents=True, exist_ok=True)
    
    def load_history(self) -> None:
        """
        Load chat history from the JSON file into memory.
        
        Reads the history file if it exists and loads the JSON data into the
        history attribute. If the file doesn't exist or is invalid, initializes
        with an empty history.
        """
        if self.history_file_path.exists():
            try:
                with open(self.history_file_path, 'r', encoding='utf-8') as file:
                    data = json.load(file)
                    if isinstance(data, list):
                        self.history = data
                    else:
                        self.history = []
            except (json.JSONDecodeError, IOError):
                self.history = []
        else:
            self.history = []
    
    def save_history(self) -> None:
        """
        Save the current in-memory history to the JSON file.
        
        Writes the history list to the file in pretty-printed JSON format
        with 4-space indentation.
        """
        with open(self.history_file_path, 'w', encoding='utf-8') as file:
            json.dump(self.history, file, indent=4, ensure_ascii=False)
    
    def add_entry(self, message) -> None:
        """
        Add a new chat entry to the history and save to file.
        
        Args:
            message (str): The message/prompt to and from the LLM.            
        """
        entry = {
            'timestamp': datetime.now().isoformat(),
            'message': message,            
        }
        
        self.history.append(entry)
        
        # Trim history if it exceeds max_history
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]
        
        self.save_history()
    
    def clear_history(self) -> None:
        """
        Clear all chat history from memory and file.
        
        Removes all entries from the in-memory history list and updates
        the file to reflect an empty history.
        """
        self.history = []
        self.save_history()
    
    
    def get_chat_history(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Retrieve chat history entries.
        
        Args:
            limit (Optional[int]): Maximum number of recent entries to return.
                                  If None, returns all entries.
        
        Returns:
            List[Dict[str, Any]]: List of history entries, most recent last.
        """
        if limit is None or limit == 0:
            return []
        xlimt = limit*2
        entries =  self.history[-xlimt:].copy() if xlimt > 0 else []
        return [entry["message"] for entry in entries]
    
    
    def get_history(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Retrieve chat history entries.
        
        Args:
            limit (Optional[int]): Maximum number of recent entries to return.
                                  If None, returns all entries.
        
        Returns:
            List[Dict[str, Any]]: List of history entries, most recent last.
        """
        if limit is None:
            return self.history.copy()
        return self.history[-limit:].copy() if limit > 0 else []
    
    def get_history_count(self) -> int:
        """
        Get the current number of history entries.
        
        Returns:
            int: The number of entries currently in history.
        """
        return len(self.history)
    
    def set_max_history(self, max_history: int) -> None:
        """
        Update the maximum number of history entries to keep.
        
        Args:
            max_history (int): New maximum number of history entries.
        """
        self.max_history = max_history
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]
            self.save_history()