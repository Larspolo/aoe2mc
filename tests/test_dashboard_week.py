"""The 7-day usage on the dashboard: `week`, `week_resets` and the on-track text of each usage row (#1696)."""
import datetime as dt

import dashboard_data
import usage

T = dt.datetime(2026, 10, 27, 12, tzinfo=dt.timezone.utc)
RESET = dt.datetime(2026, 11, 2, 14, tzinfo=dt.timezone.utc)


def line(hours, five, week, reset=True):
    t = (T + dt.timedelta(hours=hours)).timestamp()
    u = {"five_hour": (five, t + 3600, "allowed"), "seven_day": (week, RESET.timestamp(), "allowed")}
    s = usage.sample_line(u, t, 4, 80.0)
    return {"body": s if reset else s.split(" · week resets")[0]}


def test_week_track_has_three_states():
    now = RESET - dt.timedelta(hours=100)
    assert dashboard_data.week_track(0.5, RESET, now, 0.005) == "on track"           # 0.5 + 0.5 = 100 %
    assert dashboard_data.week_track(0.5, RESET, now, 0.01) == "ahead: runs out Sat 12:00"   # 50 hours after Thu 10:00
    assert dashboard_data.week_track(0.5, RESET, now, 0.002) == "behind: 30 % unused at the reset"


def test_usage_rows_have_the_week_and_its_reset():
    comments = [line(0, 0.1, 0.20, reset=False), line(1, 0.2, 0.21), line(2, 0.3, 0.22)]
    rows = dashboard_data.usage(comments=comments)
    assert [r["week"] for r in rows] == [0.20, 0.21, 0.22]
    assert {r["week_resets"] for r in rows} == {"2026-11-02T14:00:00Z"}             # the old line gets the later reset
    assert rows[0]["track"] is None                                                   # less than one hour of points
    assert rows[2]["track"] == "ahead: runs out Fri 20:00"                            # 78 % at 1 % per hour from Tue 14:00


def test_an_old_reset_moves_by_whole_weeks():
    old = {"body": line(0, 0.1, 0.2)["body"].replace("week resets 2026-11-02", "week resets 2026-10-19")}
    rows = dashboard_data.usage(comments=[old])
    assert rows[0]["week_resets"] == "2026-11-02T14:00:00Z"


def test_a_row_without_the_week_has_no_week_fields():
    t = T.timestamp()
    rows = dashboard_data.usage(comments=[{"body": usage.sample_line({"five_hour": (0.1, t, "allowed")}, t, 3)}])
    assert (rows[0]["week"], rows[0]["week_resets"], rows[0]["track"]) == (None, None, None)
