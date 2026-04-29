import json
import csv
import logging
from datetime import datetime
from pathlib import Path
from sqlalchemy.orm import Session
from sqlalchemy import select
from db.models import Account, Chat, Message, Contact
from db.session import SessionLocal

logger = logging.getLogger(__name__)


class DataExporter:
    """Export messages and metadata to JSON and CSV formats"""
    
    @staticmethod
    def export_to_json(
        output_dir: str = "./exports",
        account_id: int = None
    ) -> str:
        """Export messages to JSON format"""
        db = SessionLocal()
        try:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            # Get account
            if not account_id:
                stmt = select(Account).limit(1)
                account = db.execute(stmt).scalar_one_or_none()
                if not account:
                    logger.error("No account found")
                    return None
                account_id = account.id
            else:
                stmt = select(Account).where(Account.id == account_id)
                account = db.execute(stmt).scalar_one_or_none()
            
            # Get all chats and messages
            stmt = select(Chat).where(Chat.account_id == account_id)
            chats = db.execute(stmt).scalars().all()
            
            export_data = {
                "account": {
                    "telegram_id": account.telegram_id,
                    "username": account.username,
                    "phone_number": account.phone_number,
                    "export_date": datetime.now().isoformat()
                },
                "chats": []
            }
            
            for chat in chats:
                stmt = select(Message).where(Message.chat_id == chat.id).order_by(Message.timestamp)
                messages = db.execute(stmt).scalars().all()
                
                chat_data = {
                    "chat_id": chat.chat_id,
                    "contact_username": chat.contact_username,
                    "messages_count": len(messages),
                    "messages": [
                        {
                            "id": msg.message_id,
                            "timestamp": msg.timestamp.isoformat(),
                            "text": msg.text,
                            "sender_id": msg.sender_id,
                            "media_type": msg.media_type,
                            "media_file_id": msg.media_file_id,
                            "is_edited": msg.is_edited,
                            "is_forwarded": msg.is_forwarded,
                            "reply_to": msg.reply_to_msg_id
                        }
                        for msg in messages
                    ]
                }
                export_data["chats"].append(chat_data)
            
            # Write JSON
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            json_file = output_path / f"telegram_export_{timestamp}.json"
            
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"✓ Exported to JSON: {json_file}")
            return str(json_file)
            
        finally:
            db.close()
    
    @staticmethod
    def export_to_csv(
        output_dir: str = "./exports",
        account_id: int = None
    ) -> str:
        """Export messages to CSV format"""
        db = SessionLocal()
        try:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            # Get account
            if not account_id:
                stmt = select(Account).limit(1)
                account = db.execute(stmt).scalar_one_or_none()
                if not account:
                    logger.error("No account found")
                    return None
            
            # Get all messages
            stmt = select(Message).order_by(Message.timestamp)
            messages = db.execute(stmt).scalars().all()
            
            # Write CSV
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            csv_file = output_path / f"telegram_export_{timestamp}.csv"
            
            with open(csv_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'chat_id', 'message_id', 'sender_id', 'timestamp',
                    'text', 'media_type', 'media_file_id', 'is_edited',
                    'is_forwarded', 'reply_to'
                ])
                
                for msg in messages:
                    writer.writerow([
                        msg.chat_id,
                        msg.message_id,
                        msg.sender_id,
                        msg.timestamp.isoformat(),
                        msg.text or '',
                        msg.media_type or '',
                        msg.media_file_id or '',
                        msg.is_edited,
                        msg.is_forwarded,
                        msg.reply_to_msg_id or ''
                    ])
            
            logger.info(f"✓ Exported to CSV: {csv_file}")
            return str(csv_file)
            
        finally:
            db.close()
    
    @staticmethod
    def get_export_stats(account_id: int = None) -> dict:
        """Get statistics about exported data"""
        db = SessionLocal()
        try:
            if not account_id:
                stmt = select(Account).limit(1)
                account = db.execute(stmt).scalar_one_or_none()
                if not account:
                    return {}
                account_id = account.id
            
            stmt = select(Chat).where(Chat.account_id == account_id)
            total_chats = len(db.execute(stmt).scalars().all())
            
            stmt = select(Message).where(Message.account_id == account_id)
            messages = db.execute(stmt).scalars().all()
            total_messages = len(messages)
            
            # Calculate stats
            with_media = sum(1 for msg in messages if msg.has_media)
            edited_count = sum(1 for msg in messages if msg.is_edited)
            forwarded_count = sum(1 for msg in messages if msg.is_forwarded)
            
            return {
                "total_chats": total_chats,
                "total_messages": total_messages,
                "messages_with_media": with_media,
                "edited_messages": edited_count,
                "forwarded_messages": forwarded_count
            }
            
        finally:
            db.close()
