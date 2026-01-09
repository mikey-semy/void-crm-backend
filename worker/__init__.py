"""
Void CRM Worker - фоновая обработка задач.

Отдельное приложение на FastStream для обработки очередей RabbitMQ:
- knowledge_article_indexing: Индексация статей для RAG
- (будущее) email_notifications: Email уведомления
- (будущее) sms_notifications: SMS уведомления

Запуск:
    python -m worker.main
"""
