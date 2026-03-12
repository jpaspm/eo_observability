-- =============================================================================
-- Fluent Bit Lua Script: severity_mapper.lua
-- Enterprise Observability Platform
--
-- Maps raw log level strings from various tools to OTel severity numbers
-- per the OpenTelemetry Log Data Model specification:
-- https://opentelemetry.io/docs/specs/otel/logs/data-model/#field-severitynumber
-- =============================================================================

-- OTel SeverityNumber mapping
local SEVERITY_MAP = {
    -- TRACE (1-4)
    ["trace"]   = 1,
    ["trace2"]  = 2,
    ["trace3"]  = 3,
    ["trace4"]  = 4,
    -- DEBUG (5-8)
    ["debug"]   = 5,
    ["debug2"]  = 6,
    ["debug3"]  = 7,
    ["debug4"]  = 8,
    ["verbose"] = 5,
    ["v"]       = 5,
    -- INFO (9-12)
    ["info"]    = 9,
    ["information"] = 9,
    ["informational"] = 9,
    ["notice"]  = 10,
    -- WARN (13-16)
    ["warn"]    = 13,
    ["warning"] = 13,
    ["caution"] = 13,
    -- ERROR (17-20)
    ["error"]   = 17,
    ["err"]     = 17,
    ["severe"]  = 18,
    ["alert"]   = 18,
    -- FATAL (21-24)
    ["fatal"]   = 21,
    ["critical"] = 21,
    ["crit"]    = 21,
    ["emerg"]   = 24,
    ["emergency"] = 24,
    ["panic"]   = 24,
}

-- OTel SeverityText (canonical uppercase name)
local SEVERITY_TEXT = {
    [1]  = "TRACE",  [2]  = "TRACE2", [3]  = "TRACE3", [4]  = "TRACE4",
    [5]  = "DEBUG",  [6]  = "DEBUG2", [7]  = "DEBUG3", [8]  = "DEBUG4",
    [9]  = "INFO",   [10] = "INFO2",  [11] = "INFO3",  [12] = "INFO4",
    [13] = "WARN",   [14] = "WARN2",  [15] = "WARN3",  [16] = "WARN4",
    [17] = "ERROR",  [18] = "ERROR2", [19] = "ERROR3", [20] = "ERROR4",
    [21] = "FATAL",  [22] = "FATAL2", [23] = "FATAL3", [24] = "FATAL4",
}

--- Map raw log severity to OTel severity number and text.
-- @param tag     Fluent Bit tag string
-- @param timestamp Unix timestamp
-- @param record  Log record table
-- @return code (0=drop, 1=keep, 2=modified), timestamp, record
function map_severity(tag, timestamp, record)
    -- Find the raw level from common field names
    local raw_level = record["level"]
        or record["severity"]
        or record["log_level"]
        or record["loglevel"]
        or record["lvl"]
        or record["levelname"]   -- Python logging
        or record["PRIORITY"]    -- systemd journald
        or "info"                -- default

    local lower_level = string.lower(tostring(raw_level))

    -- Handle numeric systemd priorities (0=EMERG..7=DEBUG)
    local systemd_map = {
        ["0"] = "emerg",   ["1"] = "alert",
        ["2"] = "crit",    ["3"] = "error",
        ["4"] = "warn",    ["5"] = "notice",
        ["6"] = "info",    ["7"] = "debug",
    }
    if systemd_map[lower_level] then
        lower_level = systemd_map[lower_level]
    end

    local severity_number = SEVERITY_MAP[lower_level] or 9  -- default INFO
    local severity_text   = SEVERITY_TEXT[severity_number] or "INFO"

    -- Set OTel standard fields
    record["severity_number"] = severity_number
    record["severity_text"]   = severity_text

    -- Remove non-standard level fields (keep OTel canonical only)
    record["level"]      = nil
    record["log_level"]  = nil
    record["loglevel"]   = nil
    record["lvl"]        = nil
    record["levelname"]  = nil
    record["PRIORITY"]   = nil
    -- Keep severity as the canonical OTel text
    record["severity"]   = severity_text

    -- Tag high-severity logs for routing to quarantine/alert topics
    if severity_number >= 17 then
        record["eop.high_severity"] = "true"
    end

    return 2, timestamp, record
end
