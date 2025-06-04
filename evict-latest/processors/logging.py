from typing import Dict, List, Any
from io import BytesIO
from logging import getLogger
from datetime import datetime, timedelta

log = getLogger("evict/processors")

def process_bulk_messages(message_data: list) -> bytes:
    """
    Process bulk messages in a separate process.
    """
    return "\n".join(
        f"[{msg['created_at']}] {msg['author']} ({msg['author_id']}): {msg['content']}"
        for msg in message_data
    ).encode()

def process_message_attachments(attachment_data: list) -> list:
    """
    Process message attachments in a separate process.
    """
    return attachment_data

def process_audit_log_data(entry_data: dict) -> dict:
    """
    Process audit log data in a separate process.
    """
    processed = {
        'changes': [],
        'descriptions': []
    }
    
    if entry_data.get('before') and entry_data.get('after'):
        for field in ['name', 'color', 'permissions', 'topic', 'nsfw', 'bitrate', 'user_limit', 'slowmode_delay']:
            before = entry_data['before'].get(field)
            after = entry_data['after'].get(field)
            if before != after:
                processed['changes'].append({
                    'field': field,
                    'before': before,
                    'after': after
                })
    
    return processed

def process_audit_log_changes(before_data: dict, after_data: dict, fields: list) -> list:
    """
    Process audit log changes in a separate process.
    """
    changes = []
    
    for field in fields:
        if field == 'permissions':
            changes.append({
                'field': 'permissions',
                'before': before_data['permissions'].value, 
                'after': after_data['permissions'].value    
            })
        else:
            changes.append({
                'field': field,
                'before': str(before_data[field]),
                'after': str(after_data[field])
            })
            
    return changes

def process_account_age(created_at: datetime, current_time: datetime) -> bool:
    """
    Process account age check in a separate process.
    """
    age = current_time - created_at
    return age < timedelta(days=7)