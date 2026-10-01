-- Оперативний рівень core: нормалізована схема (НФБК, п. 2.2 курсової) з обмеженнями цілісності.
-- Порядок: таблиці → завантаження (sql/load/10_core.sql) → ключі (03_core_keys.sql).
-- Первинні й зовнішні ключі додаються після завантаження: перевірка 226 млн рядків одним
-- проходом швидша за построкову перевірку під час вставлення (PostgreSQL docs, «Populating a Database»).
DROP SCHEMA IF EXISTS core CASCADE;
CREATE SCHEMA core;

-- ---------- довідники змісту
CREATE TABLE core.part (                     -- частини іспиту TOEIC; 0 — загальні матеріали
    part_id   smallint NOT NULL CHECK (part_id BETWEEN 0 AND 7),
    section   text     CHECK (section IN ('listening', 'reading')),
    name_uk   text     NOT NULL
);

CREATE TABLE core.tag (
    tag_id    integer  NOT NULL CHECK (tag_id >= 0)
);

-- Супертип усіх елементів змісту, на які посилається журнал дій (q, b, e, l, p, c).
-- Один зовнішній ключ з core.action замість «поліморфного» текстового поля без перевірки.
CREATE TABLE core.content_item (
    item_id   text     NOT NULL,
    item_kind char(1)  NOT NULL CHECK (item_kind IN ('q', 'b', 'e', 'l', 'p', 'c')),
    CHECK (left(item_id, 1) = item_kind)
);

CREATE TABLE core.bundle (                   -- набір запитань зі спільним поясненням і частиною
    bundle_id      text     NOT NULL,
    part_id        smallint NOT NULL,
    explanation_id text     NOT NULL         -- 1:1 з набором (перевірено профілюванням)
);

CREATE TABLE core.question (
    question_id    text     NOT NULL,
    bundle_id      text     NOT NULL,
    correct_answer char(1)  NOT NULL CHECK (correct_answer IN ('a', 'b', 'c', 'd')),
    deployed_at    timestamptz               -- NULL: у джерелі -1
);

CREATE TABLE core.question_tag (             -- 1НФ: у джерелі теги — список «1;2;179» в одному полі
    question_id text    NOT NULL,
    tag_id      integer NOT NULL
);

CREATE TABLE core.lecture (
    lecture_id      text     NOT NULL,
    part_id         smallint,                -- NULL: у джерелі -1
    tag_id          integer,
    video_length_ms integer  CHECK (video_length_ms > 0),
    deployed_at     timestamptz
);

CREATE TABLE core.payment_item (
    payment_item_id text    NOT NULL,
    pass_type       text    CHECK (pass_type IN ('pass', 'paygo')),
    duration_ms     bigint  CHECK (duration_ms > 0),
    question_count  integer CHECK (question_count > 0)
);

CREATE TABLE core.coupon (
    coupon_id   text   NOT NULL,
    coupon_type text   NOT NULL,
    duration_ms bigint NOT NULL CHECK (duration_ms > 0)
);

-- ---------- довідники подій
CREATE TABLE core.action_type (action_type_id smallint NOT NULL, name text NOT NULL);
CREATE TABLE core.source      (source_id      smallint NOT NULL, name text NOT NULL);
CREATE TABLE core.platform    (platform_id    smallint NOT NULL, name text NOT NULL);

-- ---------- користувачі й журнали
CREATE TABLE core.app_user (
    user_id       bigint      NOT NULL CHECK (user_id > 0),
    first_seen_at timestamptz NOT NULL
);

-- Сесія розв'язування набору: час показу і витрачений час — властивості сесії, а не кожної відповіді.
-- У плоскому KT1 вони повторюються в кожному рядку сесії і в 462 550 сесіях розійшлися (аномалія оновлення).
CREATE TABLE core.solving_session (
    user_id    bigint      NOT NULL,
    solving_id integer     NOT NULL CHECK (solving_id > 0),
    bundle_id  text        NOT NULL,
    started_at timestamptz NOT NULL,
    elapsed_ms integer     CHECK (elapsed_ms >= 0)       -- NULL: не додатне значення в джерелі
);

CREATE TABLE core.answer (
    user_id     bigint      NOT NULL,
    solving_id  integer     NOT NULL,
    question_id text        NOT NULL,
    user_answer char(1)     CHECK (user_answer IN ('a', 'b', 'c', 'd')),   -- NULL: запитання пропущено
    answered_at timestamptz NOT NULL
);

CREATE TABLE core.action (
    action_id      bigint      GENERATED ALWAYS AS IDENTITY,
    user_id        bigint      NOT NULL,
    occurred_at    timestamptz NOT NULL,
    action_type_id smallint    NOT NULL,
    item_id        text,                      -- NULL: у джерелі '-1' (722 події відтворення)
    source_id      smallint,
    platform_id    smallint,
    user_answer    char(1)     CHECK (user_answer IN ('a', 'b', 'c', 'd')),
    cursor_time_ms integer     CHECK (cursor_time_ms >= 0)
);
