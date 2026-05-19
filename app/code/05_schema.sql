-- =============================================================================
-- Claude Agent SDK — MySQL Database Schema
-- =============================================================================
-- Manual alternative to running 04_init_db.py.
--
-- Usage:
--   mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS claude_agent_sdk \
--     CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
--   mysql -u root -p claude_agent_sdk < app/code/05_schema.sql
--
-- NOTE: Column `extra_data` is used instead of `metadata` everywhere.
-- SQLAlchemy reserves the name `metadata` on model classes.
-- =============================================================================

SET NAMES utf8mb4;

-- =============================================================================
-- USERS & SESSIONS
-- =============================================================================

CREATE TABLE IF NOT EXISTS users (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    username    VARCHAR(100)  NOT NULL,
    email       VARCHAR(255)  NULL,
    session_id  VARCHAR(255)  NULL COMMENT 'UUID stored in frontend localStorage',
    created_at  DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_active DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP
                              ON UPDATE CURRENT_TIMESTAMP,
    extra_data  JSON          NULL,
    UNIQUE INDEX idx_username   (username),
    UNIQUE INDEX idx_email      (email),
    UNIQUE INDEX idx_session_id (session_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- =============================================================================
-- CONVERSATIONS
-- =============================================================================

CREATE TABLE IF NOT EXISTS conversations (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    user_id     INT           NOT NULL,
    title       VARCHAR(255)  NOT NULL DEFAULT 'New Conversation',
    description TEXT          NULL,
    created_at  DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP
                              ON UPDATE CURRENT_TIMESTAMP,
    is_archived TINYINT(1)    NOT NULL DEFAULT 0,
    extra_data  JSON          NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_conv_user_id   (user_id),
    INDEX idx_conv_created   (created_at),
    INDEX idx_conv_updated   (updated_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- =============================================================================
-- MESSAGES
-- =============================================================================

CREATE TABLE IF NOT EXISTS messages (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    conversation_id INT           NOT NULL,
    role            VARCHAR(50)   NOT NULL COMMENT 'user | assistant',
    content         LONGTEXT      NOT NULL,
    created_at      DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    extra_data      JSON          NULL,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
    INDEX idx_msg_conv_id  (conversation_id),
    INDEX idx_msg_created  (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- =============================================================================
-- TOOL CALLS
-- =============================================================================

CREATE TABLE IF NOT EXISTS tool_calls (
    id               INT AUTO_INCREMENT PRIMARY KEY,
    message_id       INT           NOT NULL,
    tool_name        VARCHAR(100)  NOT NULL,
    tool_input       JSON          NOT NULL,
    tool_output      JSON          NULL,
    status           VARCHAR(50)   NOT NULL DEFAULT 'triggered'
                     COMMENT 'triggered | success | error',
    error_message    TEXT          NULL,
    created_at       DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at     DATETIME      NULL,
    execution_time_ms FLOAT        NULL,
    FOREIGN KEY (message_id) REFERENCES messages(id) ON DELETE CASCADE,
    INDEX idx_tc_message_id (message_id),
    INDEX idx_tc_tool_name  (tool_name),
    INDEX idx_tc_status     (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- =============================================================================
-- INVENTORY ITEMS  (replaces app/csv/inventry.csv)
-- =============================================================================

CREATE TABLE IF NOT EXISTS inventory_items (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    user_id     INT           NULL COMMENT 'NULL = global/shared item',
    sku         VARCHAR(100)  NOT NULL,
    name        VARCHAR(255)  NOT NULL,
    quantity    INT           NOT NULL DEFAULT 0,
    price       FLOAT         NULL,
    description TEXT          NULL,
    created_at  DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP
                              ON UPDATE CURRENT_TIMESTAMP,
    extra_data  JSON          NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
    UNIQUE INDEX idx_inv_sku      (sku),
    INDEX        idx_inv_user_id  (user_id),
    INDEX        idx_inv_updated  (updated_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- =============================================================================
-- USER NOTES  (replaces in-memory _notes dict in mcp_servers/notes_server.py)
-- =============================================================================

CREATE TABLE IF NOT EXISTS user_notes (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    user_id     INT           NOT NULL,
    title       VARCHAR(255)  NOT NULL,
    content     LONGTEXT      NOT NULL,
    created_at  DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP
                              ON UPDATE CURRENT_TIMESTAMP,
    is_pinned   TINYINT(1)    NOT NULL DEFAULT 0,
    extra_data  JSON          NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_note_user_id (user_id),
    INDEX idx_note_updated (updated_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- =============================================================================
-- AUDIT LOGS
-- =============================================================================

CREATE TABLE IF NOT EXISTS audit_logs (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    user_id       INT           NULL COMMENT 'Survives user deletion — no FK',
    action        VARCHAR(100)  NOT NULL,
    resource_type VARCHAR(50)   NOT NULL,
    resource_id   INT           NULL,
    details       JSON          NULL,
    created_at    DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_audit_user_id  (user_id),
    INDEX idx_audit_action   (action),
    INDEX idx_audit_created  (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- =============================================================================
-- SEED: inventory from original CSV (run once; skip if rows exist)
-- =============================================================================

INSERT IGNORE INTO inventory_items (sku, name, quantity)
VALUES
    ('BATS-001',  'bats',  10),
    ('BALLS-001', 'balls',  6),
    ('CAPS-001',  'caps',   5);


-- =============================================================================
-- VERIFY
-- =============================================================================

SELECT
    table_name,
    table_rows AS approx_rows
FROM information_schema.tables
WHERE table_schema = DATABASE()
ORDER BY table_name;
