-- Разове виправлення після першого запуску: у 722 подіях відтворення недійсний елемент записаний як '-1',
-- а правило очищення перевіряло '-'. Зовнішній ключ на core.action.item_id не дав завершити завантаження.
-- Після виправлення правила в 10_core.sql повторний повний запуск цього скрипта не потребує.
UPDATE core.action SET item_id = NULL WHERE item_id = '-1';
ALTER TABLE core.action          ADD PRIMARY KEY (action_id),
                                 ADD FOREIGN KEY (user_id)        REFERENCES core.app_user,
                                 ADD FOREIGN KEY (action_type_id) REFERENCES core.action_type,
                                 ADD FOREIGN KEY (item_id)        REFERENCES core.content_item,
                                 ADD FOREIGN KEY (source_id)      REFERENCES core.source,
                                 ADD FOREIGN KEY (platform_id)    REFERENCES core.platform;
ANALYZE;
