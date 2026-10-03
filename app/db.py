import json
from collections.abc import Generator

from sqlalchemy import event, inspect, text
from sqlalchemy.engine import Engine
from sqlmodel import Session, SQLModel, create_engine, select

from app.config import ROOT, get_settings
from app.models import Badge, Streak, Topic, User

settings = get_settings()
if settings.database_url.startswith("sqlite:///"):
    db_path = ROOT / settings.database_url.removeprefix("sqlite:///")
    db_path.parent.mkdir(parents=True, exist_ok=True)

engine: Engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},
    pool_pre_ping=True,
)

if settings.database_url.startswith("sqlite"):

    @event.listens_for(engine, "connect")
    def configure_sqlite(connection, _record) -> None:
        cursor = connection.cursor()
        cursor.execute("PRAGMA busy_timeout=30000")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()


TOPICS = [
    ("My Dream Weekend", "What would your perfect weekend look like?"),
    ("School Life", "What made you smile at school this week?"),
    ("Favorite Music", "Which song always lifts your mood, and why?"),
    ("Food Adventure", "What food would you love to learn to cook?"),
    ("Future Travel", "Where would you go if you could fly anywhere tomorrow?"),
    ("Best Friends", "What makes someone a really good friend?"),
    ("Movies and Shows", "Which character would you like to meet?"),
    ("Amazing Animals", "Which animal do you find most interesting?"),
    ("My Superpower", "What superpower would help people around you?"),
    ("Fashion and Style", "Which outfit makes you feel most confident?"),
    ("Sports and Movement", "What kind of movement makes you feel energized?"),
    ("Books I Love", "Which book world would you visit for one day?"),
    ("Creative Hobbies", "What do you enjoy making with your hands?"),
    ("Hong Kong Favorites", "Where would you take a friend visiting Hong Kong?"),
    ("Planet Protector", "What small action could make Earth happier?"),
    ("Tech Tomorrow", "What useful app would you invent?"),
    ("Kindness Challenge", "When did someone surprise you with kindness?"),
    ("Mystery Story", "You hear a sound behind a door. What happens next?"),
    ("My Proud Moment", "What is something brave you did recently?"),
    ("Dream Job", "What would you love to create or change when you grow up?"),
]

BADGES = [
    ("first-flight", "First Flight", "首次启航", "Complete one quest."),
    ("seven-day", "7-Day Streak", "七日连击", "Practice for seven days."),
    ("loud-proud", "Loud & Proud", "大声自豪", "Speak strongly for 20 seconds."),
    ("word-collector", "Word Collector", "单词收藏家", "Echo 50 new words."),
    ("topic-creator", "Topic Creator", "主题创作者", "Create a voice topic."),
    ("challenger", "Challenger", "挑战者", "Complete a Challenge quest."),
    ("early-bird", "Early Bird", "早起鸟", "Finish three early quests."),
    ("weekend", "Weekend Warrior", "周末勇士", "Practice on a weekend."),
    ("perfect-score", "Perfect Score", "满分之星", "Average at least 95."),
    ("comeback", "Comeback Kid", "勇敢回归", "Return after three days."),
    ("echo-master", "Echo Master", "回声大师", "Earn 30 Echo Bonuses."),
    ("loud-legend", "Loud Legend", "响亮传奇", "Speak loudly for five minutes."),
    ("daily-shouter", "Daily Shouter", "每日呐喊者", "Finish ten shout-outs."),
]


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session


def seed_data(session: Session) -> None:
    if not session.exec(select(User).where(User.username.is_(None))).first():
        user = User(nickname="Guest")
        session.add(user)
        session.commit()
        session.refresh(user)
        session.add(Streak(user_id=user.id or 1))

    if not session.exec(select(Topic)).first():
        for index, (title, question) in enumerate(TOPICS):
            difficulty = ("easy", "normal", "hard", "expert")[index % 4]
            session.add(
                Topic(
                    title=title,
                    difficulty=difficulty,
                    starter_question=question,
                    follow_up_hints_json=json.dumps(
                        ["Tell me more.", "How did that feel?", "Why is it special?"]
                    ),
                    ideal_answer=f"I think {title.lower()} is special because...",
                    suggested_words_json=json.dumps(
                        ["confident", "memorable", "curious"]
                    ),
                )
            )

    if not session.exec(select(Badge)).first():
        for code, en, zh, description in BADGES:
            session.add(
                Badge(
                    code=code,
                    name_en=en,
                    name_zh=zh,
                    desc_en=description,
                    desc_zh=description,
                    svg_path=f"/static/badges/{code}.svg",
                )
            )
    session.commit()


def migrate_schema() -> None:
    tables = inspect(engine).get_table_names()
    if "users" not in tables:
        return
    columns = {item["name"] for item in inspect(engine).get_columns("users")}
    topic_columns = {item["name"] for item in inspect(engine).get_columns("topics")}
    daily_columns = (
        {item["name"] for item in inspect(engine).get_columns("daily_practice_content")}
        if "daily_practice_content" in tables
        else set()
    )
    with engine.begin() as connection:
        if "username" not in columns:
            connection.execute(text("ALTER TABLE users ADD COLUMN username VARCHAR"))
        if "password_hash" not in columns:
            connection.execute(
                text("ALTER TABLE users ADD COLUMN password_hash VARCHAR")
            )
        if "daily_content_id" not in topic_columns:
            connection.execute(
                text("ALTER TABLE topics ADD COLUMN daily_content_id INTEGER")
            )
        if daily_columns and "source_release_id" not in daily_columns:
            connection.execute(
                text(
                    "ALTER TABLE daily_practice_content "
                    "ADD COLUMN source_release_id INTEGER"
                )
            )
        connection.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_daily_content_source_release "
                "ON daily_practice_content(source_release_id)"
            )
        )
        connection.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS ux_users_username "
                "ON users(username) WHERE username IS NOT NULL"
            )
        )
        for table in ("users", "topics", "sessions"):
            column = "default_difficulty" if table == "users" else "difficulty"
            connection.execute(
                text(
                    f"UPDATE {table} SET {column} = 'normal' "
                    f"WHERE {column} = 'medium'"
                )
            )
            connection.execute(
                text(
                    f"UPDATE {table} SET {column} = 'hard' "
                    f"WHERE {column} = 'challenge'"
                )
            )


def init_db() -> None:
    migrate_schema()
    SQLModel.metadata.create_all(engine)
    migrate_schema()
    with Session(engine) as session:
        seed_data(session)
