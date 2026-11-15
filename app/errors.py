import traceback

from flask import jsonify, render_template, request
from werkzeug.exceptions import HTTPException


class DomainError(Exception):
    status_code = 500

    def __init__(self, code, message, details=None):
        super().__init__(message)
        self.code, self.message, self.details = code, message, details or {}


class ValidationError(DomainError):
    status_code = 422


class NotFoundError(DomainError):
    status_code = 404

    def __init__(self):
        super().__init__('not_found', 'Заказ не найден. Проверьте ссылку из чека.')


class ConflictError(DomainError):
    status_code = 409

    def __init__(self):
        super().__init__('idempotency_conflict', 'Эта попытка оформления уже использована для другой корзины.')


def register_errors(app):
    @app.errorhandler(Exception)
    def handle_error(error):
        if isinstance(error, DomainError):
            status, code, message, details = error.status_code, error.code, error.message, error.details
        elif isinstance(error, HTTPException):
            status, code, details = error.code, error.name.lower().replace(' ', '_'), {}
            message = {400: 'Не удалось прочитать JSON запроса.', 404: 'Страница не найдена.',
                       405: 'Этот метод запроса не поддерживается.', 413: 'Запрос слишком большой. Лимит — 16 КиБ.',
                       415: 'Отправьте запрос с Content-Type: application/json.'}.get(status, 'Не удалось выполнить запрос.')
        else:
            status, code, message, details = 500, 'internal_error', 'Что-то пошло не так. Попробуйте ещё раз чуть позже.', {}
            # Exception text can include SQL parameters (including bearer tokens).
            app.logger.error('Unhandled application error: %s\n%s', type(error).__name__, ''.join(traceback.format_tb(error.__traceback__)))
        if request.path.startswith('/api/'):
            return jsonify(error={'code': code, 'message': message, 'details': details}), status
        return render_template('404.html' if status == 404 else '500.html', message=message), status
