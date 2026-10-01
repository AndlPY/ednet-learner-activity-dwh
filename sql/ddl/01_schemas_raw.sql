-- Схеми рівнів зберігання і сирий рівень (raw).
-- raw — копія джерела з типами, без обмежень цілісності: сюди потрапляє все, навіть дублікати,
-- щоб будь-яке перетворення можна було повторити без повторного читання архівів.
CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS core;
CREATE SCHEMA IF NOT EXISTS marts;

DROP TABLE IF EXISTS raw.kt1, raw.kt4, raw.questions, raw.lectures, raw.payments, raw.coupons;

CREATE TABLE raw.kt1 (          -- журнал відповідей, 95 293 926 рядків
    user_id      bigint,
    ts           bigint,        -- мс від 1970-01-01 UTC
    solving_id   bigint,
    question_id  text,
    user_answer  text,
    elapsed_time bigint         -- мс
);

CREATE TABLE raw.kt4 (          -- повний журнал дій, 131 441 538 рядків
    user_id      bigint,
    ts           bigint,
    action_type  text,
    item_id      text,
    cursor_time  bigint,
    source       text,
    user_answer  text,
    platform     text
);

CREATE TABLE raw.questions (question_id text, bundle_id text, explanation_id text, correct_answer text,
                            part text, tags text, deployed_at text);
CREATE TABLE raw.lectures  (lecture_id text, part text, tags text, video_length text, deployed_at text);
CREATE TABLE raw.payments  (payment_item_id text, type text, duaration text, number_of_questions text);
CREATE TABLE raw.coupons   (coupon_id text, coupon_type text, duration text);
