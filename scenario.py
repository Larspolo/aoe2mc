import contextlib, io, os, sys, tempfile
sys.path[:0] = ["/home/user/aoe2mc", "/home/user/aoe2mc/tools"]
import scenarios
from AoE2ScenarioParser.datasets.units import UnitInfo
from AoE2ScenarioParser.datasets.buildings import BuildingInfo
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario

def build(path):
    with contextlib.redirect_stdout(io.StringIO()), tempfile.TemporaryDirectory() as tmp:
        scn = AoE2DEScenario.from_file(scenarios.tiny(os.path.join(tmp, "t.aoe2scenario")))
    um, tm = scn.unit_manager, scn.trigger_manager
    house = next(u for u in um.get_player_units(1) if u.unit_const == BuildingInfo.HOUSE.ID)
    ship = um.add_unit(1, UnitInfo.TRANSPORT_SHIP.ID, x=21.5, y=16.5)
    old = um.add_unit(1, BuildingInfo.HOUSE.ID, x=8, y=21)
    def trig(name, msg):
        t = tm.add_trigger(name); return t
    def chat(t, m): t.new_effect.send_chat(source_player=1, message=m)
    t = tm.add_trigger("2 damage"); t.new_condition.timer(timer=5)
    t.new_effect.damage_object(quantity=300, source_player=1, object_list_unit_id=BuildingInfo.HOUSE.ID, area_x1=3, area_y1=15, area_x2=5, area_y2=17)
    chat(t, "Item 2: the house takes 300 damage.")
    t = tm.add_trigger("2 heal"); t.new_condition.timer(timer=15)
    t.new_effect.damage_object(quantity=-200, source_player=1, object_list_unit_id=BuildingInfo.HOUSE.ID, area_x1=3, area_y1=15, area_x2=5, area_y2=17)
    chat(t, "Item 2: the house heals 200.")
    t = tm.add_trigger("1 attacked"); t.new_condition.object_attacked(source_player=1, unit_object=house.reference_id)
    chat(t, "Item 1: the house is attacked.")
    t = tm.add_trigger("3 disable"); t.new_condition.timer(timer=3)
    t.new_effect.disable_object_deletion(source_player=1, selected_object_ids=[house.reference_id])
    chat(t, "Item 3: the house cannot be deleted.")
    t = tm.add_trigger("3 enable"); t.new_condition.timer(timer=40)
    t.new_effect.enable_object_deletion(source_player=1, selected_object_ids=[house.reference_id])
    chat(t, "Item 3: the house can be deleted again.")
    t = tm.add_trigger("4 replace"); t.new_condition.timer(timer=8)
    t.new_effect.replace_object(source_player=1, target_player=1, object_list_unit_id=BuildingInfo.HOUSE.ID, object_list_unit_id_2=BuildingInfo.BLACKSMITH.ID, area_x1=7, area_y1=20, area_x2=9, area_y2=22)
    chat(t, "Item 4: the house at (8, 21) is a blacksmith now.")
    t = tm.add_trigger("5 create"); t.new_condition.timer(timer=10)
    t.new_effect.create_garrisoned_object(source_player=1, object_list_unit_id_2=UnitInfo.MILITIA.ID, selected_object_ids=[ship.reference_id])
    chat(t, "Item 5: a militia is in the transport ship.")
    t = tm.add_trigger("6 garrisoned"); t.new_condition.units_garrisoned(quantity=1, unit_object=ship.reference_id)
    chat(t, "Item 6: the transport ship holds a unit.")
    t = tm.add_trigger("5 unload"); t.new_condition.timer(timer=25)
    t.new_effect.unload(source_player=1, location_x=16, location_y=16, selected_object_ids=[ship.reference_id])
    chat(t, "Item 5: the ship unloads.")
    t = tm.add_trigger("7 victory"); t.new_condition.timer(timer=4)
    t.new_condition.victory_timer(quantity=20, source_player=1, inverted=1, comparison=0, victory_timer_type=0)
    chat(t, "Item 7: no victory timer of player 1 runs.")
    t = tm.add_trigger("8 bring"); t.new_condition.timer(timer=6)
    t.new_condition.bring_object_to_area(unit_object=house.reference_id, area_x1=3, area_y1=15, area_x2=5, area_y2=17)
    chat(t, "Item 8: the house is in the area.")
    t = tm.add_trigger("8 bring object");
    knight = next(u for u in um.get_player_units(1) if u.unit_const == UnitInfo.KNIGHT.ID)
    t.new_condition.bring_object_to_object(unit_object=knight.reference_id, next_object=house.reference_id)
    chat(t, "Item 8: the knight is at the house.")
    print("house", house.reference_id, "ship", ship.reference_id, "old", old.reference_id, "knight", knight.reference_id)
    return scenarios.save(scn, path)

if __name__ == "__main__":
    build(sys.argv[1])
