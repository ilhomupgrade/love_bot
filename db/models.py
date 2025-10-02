"""
SQLAlchemy модели для базы данных
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, func, UniqueConstraint, Index
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Session(Base):
    """Сессия тестирования пары"""
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=func.now())
    status = Column(String, default="pending")  # pending, in_progress, completed, quick_check
    partner1_user_id = Column(Integer, nullable=True)  # Telegram user ID первого партнёра
    partner2_user_id = Column(Integer, nullable=True)  # Telegram user ID второго партнёра

    answers = relationship("Answer", back_populates="session", cascade="all, delete-orphan")
    result = relationship("Result", back_populates="session", uselist=False, cascade="all, delete-orphan")


class Answer(Base):
    """Ответы партнёров на вопросы"""
    __tablename__ = "answers"
    __table_args__ = (
        UniqueConstraint('session_id', 'user_id', name='uq_session_user'),
        Index('idx_user_completed', 'user_id', 'completed_at'),
    )

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False)
    user_id = Column(Integer, nullable=False)  # Telegram user ID
    user_role = Column(String, nullable=False)  # partner1 или partner2
    answers = Column(JSON, nullable=False)  # список ответов
    completed_at = Column(DateTime, default=func.now())

    session = relationship("Session", back_populates="answers")


class Result(Base):
    """Результаты анализа совместимости"""
    __tablename__ = "results"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False)
    compatibility_score = Column(Integer, nullable=False)  # 0-100
    report = Column(String, nullable=False)  # полный отчёт от AI
    created_at = Column(DateTime, default=func.now())

    session = relationship("Session", back_populates="result")
