"""The parser of `jfr print` text in tools/server_profile.py (#3336)."""
import server_profile

TEXT = """jdk.ExecutionSample {
  startTime = 21:36:30.234 (2026-10-28)
  sampledThread = "Server thread" (javaThreadId = 51)
  state = "STATE_RUNNABLE"
  stackTrace = [
    net.minecraft.world.entity.ai.behavior.YieldJobSite.canReachPos(Villager, BlockPos) line: 70
    net.minecraft.server.level.ServerLevel.tick(BooleanSupplier) line: 818
    net.minecraft.server.MinecraftServer.tickServer(BooleanSupplier) line: 1604
    ...
  ]
}

jdk.ExecutionSample {
  startTime = 21:36:30.285 (2026-10-28)
  sampledThread = "Worker-Main-1" (javaThreadId = 60)
  state = "STATE_RUNNABLE"
  stackTrace = [
    java.util.HashMap.get(Object) line: 1
  ]
}

jdk.ExecutionSample {
  startTime = 21:36:30.834 (2026-10-28)
  sampledThread = "Server thread" (javaThreadId = 51)
  state = "STATE_RUNNABLE"
  stackTrace = [
    net.minecraft.world.attribute.EnvironmentAttributeSystem$ValueSampler.getDimensionValue() line: 257
    net.minecraft.server.level.ServerLevel.tick(BooleanSupplier) line: 818
    net.minecraft.server.MinecraftServer.tickServer(BooleanSupplier) line: 1604
  ]
}
"""


def test_only_the_server_thread():
    own, incl, n = server_profile.count(server_profile.samples(TEXT.splitlines(True)))
    assert n == 2
    assert own["net.minecraft.world.entity.ai.behavior.YieldJobSite.canReachPos"] == 1
    assert own["net.minecraft.world.attribute.EnvironmentAttributeSystem$ValueSampler.getDimensionValue"] == 1
    assert incl["net.minecraft.server.level.ServerLevel.tick"] == 2
    assert "java.util.HashMap.get" not in incl


def test_table():
    t = server_profile.table(*server_profile.count(server_profile.samples(TEXT.splitlines(True))), top=2)
    assert t.startswith("2 samples of the Server thread")
    assert "100.0        2  net.minecraft.server.level.ServerLevel.tick" in t
    assert "method (own)" in t and "method (inclusive)" in t
