from unittest.mock import MagicMock, patch


def test_get_db_closes_session_after_generator_close():
    with patch("app.db.session.SessionLocal") as session_local:
        sess = MagicMock()
        session_local.return_value = sess
        from app.db.session import get_db

        gen = get_db()
        assert next(gen) is sess
        gen.close()
        sess.close.assert_called_once()
