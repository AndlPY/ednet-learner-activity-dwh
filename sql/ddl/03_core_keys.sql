-- Ключі core: після завантаження. Кожен FK перевіряється одним проходом по таблиці.
ALTER TABLE core.part            ADD PRIMARY KEY (part_id);
ALTER TABLE core.tag             ADD PRIMARY KEY (tag_id);
ALTER TABLE core.content_item    ADD PRIMARY KEY (item_id);
ALTER TABLE core.bundle          ADD PRIMARY KEY (bundle_id),
                                 ADD UNIQUE (explanation_id),
                                 ADD FOREIGN KEY (bundle_id)      REFERENCES core.content_item,
                                 ADD FOREIGN KEY (explanation_id) REFERENCES core.content_item,
                                 ADD FOREIGN KEY (part_id)        REFERENCES core.part;
ALTER TABLE core.question        ADD PRIMARY KEY (question_id),
                                 ADD FOREIGN KEY (question_id) REFERENCES core.content_item,
                                 ADD FOREIGN KEY (bundle_id)   REFERENCES core.bundle;
ALTER TABLE core.question_tag    ADD PRIMARY KEY (question_id, tag_id),
                                 ADD FOREIGN KEY (question_id) REFERENCES core.question,
                                 ADD FOREIGN KEY (tag_id)      REFERENCES core.tag;
ALTER TABLE core.lecture         ADD PRIMARY KEY (lecture_id),
                                 ADD FOREIGN KEY (lecture_id) REFERENCES core.content_item,
                                 ADD FOREIGN KEY (part_id)    REFERENCES core.part,
                                 ADD FOREIGN KEY (tag_id)     REFERENCES core.tag;
ALTER TABLE core.payment_item    ADD PRIMARY KEY (payment_item_id),
                                 ADD FOREIGN KEY (payment_item_id) REFERENCES core.content_item;
ALTER TABLE core.coupon          ADD PRIMARY KEY (coupon_id),
                                 ADD FOREIGN KEY (coupon_id) REFERENCES core.content_item;
ALTER TABLE core.action_type     ADD PRIMARY KEY (action_type_id), ADD UNIQUE (name);
ALTER TABLE core.source          ADD PRIMARY KEY (source_id),      ADD UNIQUE (name);
ALTER TABLE core.platform        ADD PRIMARY KEY (platform_id),    ADD UNIQUE (name);
ALTER TABLE core.app_user        ADD PRIMARY KEY (user_id);
ALTER TABLE core.solving_session ADD PRIMARY KEY (user_id, solving_id),
                                 ADD FOREIGN KEY (user_id)   REFERENCES core.app_user,
                                 ADD FOREIGN KEY (bundle_id) REFERENCES core.bundle;
ALTER TABLE core.answer          ADD PRIMARY KEY (user_id, solving_id, question_id),
                                 ADD FOREIGN KEY (user_id, solving_id) REFERENCES core.solving_session,
                                 ADD FOREIGN KEY (question_id)         REFERENCES core.question;
ALTER TABLE core.action          ADD PRIMARY KEY (action_id),
                                 ADD FOREIGN KEY (user_id)        REFERENCES core.app_user,
                                 ADD FOREIGN KEY (action_type_id) REFERENCES core.action_type,
                                 ADD FOREIGN KEY (item_id)        REFERENCES core.content_item,
                                 ADD FOREIGN KEY (source_id)      REFERENCES core.source,
                                 ADD FOREIGN KEY (platform_id)    REFERENCES core.platform;
ANALYZE;
