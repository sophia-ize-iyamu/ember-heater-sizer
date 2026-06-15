"""
Ember: an industrial electric heater sizing and quoting tool.

Given a heating application (heat a volume of fluid to a target temperature in a set
time, then hold it), Ember sizes the required power, checks watt density against the
fluid limit, picks a standard rating and element count, builds a bill of materials,
and prices a quote. It is a small model of what an application engineer does at a
process-heating company: size the right solution, then cost and quote it.

Engineering basis:
  Sensible heat       Q = m * cp * dT
  Heat-up power       P_heatup = Q / heat-up time
  Standby loss        P_loss   = UA * (T_operate - T_ambient)
  Watt density check  W/in^2 on the sheath must stay under the fluid limit, or the
                      film overheats (coking oils, scaling water). This usually drives
                      the element count, not the total power.

References: heat-transfer fundamentals (Incropera, Fundamentals of Heat and Mass
Transfer); industry heater-sizing and watt-density guidance (Chromalox and Watlow
application guides). Prices are illustrative, not a real price list.
"""
import math, os

FLUIDS = {
    # rho kg/m3, cp J/kgK, watt-density limit W/in^2 on the sheath (protects the film)
    "water":             dict(rho=997, cp=4186, wd_limit=45),
    "light oil":         dict(rho=870, cp=1900, wd_limit=23),
    "heat-transfer oil": dict(rho=850, cp=2000, wd_limit=18),
}
STANDARD_KW = [3, 6, 9, 12, 18, 24, 30, 36, 45, 54, 72, 90, 120]  # catalog ratings
ELEMENT_AREA_IN2 = 60          # effective sheath area per immersion element (illustrative)
PRICES = dict(heater_per_kw=42.0, element=85.0, controller=480.0,
              high_limit=190.0, thermowell=70.0, enclosure=520.0)  # USD, illustrative
MARGIN = 0.35


def size(app):
    f = FLUIDS[app["fluid"]]
    mass = app["volume_m3"] * f["rho"]
    dT = app["t_target_C"] - app["t_initial_C"]
    q_kwh = mass * f["cp"] * dT / 3.6e6
    heatup_kw = q_kwh / app["heatup_h"]
    loss_kw = app["UA_W_per_K"] * (app["t_target_C"] - app["t_ambient_C"]) / 1000.0
    required_kw = (heatup_kw + loss_kw) * app["safety_factor"]
    rating_kw = next((r for r in STANDARD_KW if r >= required_kw), STANDARD_KW[-1])
    # spread the power over enough element area to stay under the watt-density limit
    area_needed = rating_kw * 1000 / f["wd_limit"]
    elements = max(1, math.ceil(area_needed / ELEMENT_AREA_IN2))
    actual_wd = rating_kw * 1000 / (elements * ELEMENT_AREA_IN2)
    return dict(mass=mass, dT=dT, q_kwh=q_kwh, heatup_kw=heatup_kw, loss_kw=loss_kw,
                required_kw=required_kw, rating_kw=rating_kw, elements=elements,
                actual_wd=actual_wd, wd_limit=f["wd_limit"])


def quote(s):
    items = [
        (f"Flanged immersion heater body, {s['rating_kw']} kW", 1, PRICES["heater_per_kw"] * s["rating_kw"]),
        ("Sheathed heating elements", s["elements"], PRICES["element"]),
        ("Digital temperature controller", 1, PRICES["controller"]),
        ("High-limit safety thermostat", 1, PRICES["high_limit"]),
        ("Thermowell with RTD", 1, PRICES["thermowell"]),
        ("Terminal enclosure, NEMA 4", 1, PRICES["enclosure"]),
    ]
    rows = [(name, qty, unit, qty * unit) for name, qty, unit in items]
    material = sum(r[3] for r in rows)
    return rows, material, material * (1 + MARGIN)


def write_report(app, s, rows, material, price):
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
    os.makedirs(out, exist_ok=True)
    L = []
    L.append("# Ember sizing and quote\n")
    L.append(f"**Application:** heat {app['volume_m3']*264.17:.0f} gal of {app['fluid']} "
             f"from {app['t_initial_C']} to {app['t_target_C']} C in {app['heatup_h']} h, "
             f"then hold at {app['t_target_C']} C.\n")
    L.append("## Sizing\n")
    L.append(f"- Mass heated: {s['mass']:.0f} kg, temperature rise {s['dT']:.0f} C")
    L.append(f"- Sensible heat: {s['q_kwh']:.1f} kWh")
    L.append(f"- Heat-up power: {s['heatup_kw']:.1f} kW")
    L.append(f"- Standby loss at temperature: {s['loss_kw']:.2f} kW")
    L.append(f"- Required with {app['safety_factor']:.2f} safety factor: {s['required_kw']:.1f} kW")
    L.append(f"- **Selected standard rating: {s['rating_kw']} kW**\n")
    L.append("## Watt-density check\n")
    L.append(f"- Limit for {app['fluid']}: {s['wd_limit']} W/in^2")
    L.append(f"- Elements needed to stay under the limit: {s['elements']}")
    L.append(f"- Actual watt density: {s['actual_wd']:.1f} W/in^2 "
             f"({'OK' if s['actual_wd'] <= s['wd_limit'] else 'OVER LIMIT'})\n")
    L.append("## Bill of materials and quote\n")
    L.append("| Item | Qty | Unit (USD) | Ext (USD) |")
    L.append("|---|---|---|---|")
    for name, qty, unit, ext in rows:
        L.append(f"| {name} | {qty} | {unit:,.2f} | {ext:,.2f} |")
    L.append(f"\n- Material cost: ${material:,.2f}")
    L.append(f"- Margin: {MARGIN:.0%}")
    L.append(f"- **Quoted price: ${price:,.2f}**\n")
    open(os.path.join(out, "quote.md"), "w", encoding="utf-8").write("\n".join(L))

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(6, 3.2))
        labels = ["Heat-up", "Standby loss", "Safety margin", "Selected"]
        margin_kw = s["required_kw"] - (s["heatup_kw"] + s["loss_kw"])
        vals = [s["heatup_kw"], s["loss_kw"], margin_kw, s["rating_kw"]]
        ax.bar(labels, vals, color=["#C9A24A", "#C9A24A", "#d8c089", "#1a1a1a"])
        ax.set_ylabel("Power (kW)")
        ax.set_title("Heater sizing breakdown")
        fig.tight_layout()
        fig.savefig(os.path.join(out, "sizing.png"), dpi=130)
    except Exception as e:
        print(f"(figure skipped: {e})")


def main():
    app = dict(fluid="heat-transfer oil", volume_m3=0.757, t_initial_C=20, t_target_C=150,
               heatup_h=2.0, t_ambient_C=20, UA_W_per_K=3.0, safety_factor=1.2)
    s = size(app)
    rows, material, price = quote(s)
    print(f"Required {s['required_kw']:.1f} kW -> selected {s['rating_kw']} kW, "
          f"{s['elements']} elements at {s['actual_wd']:.1f} W/in^2 "
          f"(limit {s['wd_limit']}).")
    print(f"Material ${material:,.0f}, quoted ${price:,.0f} at {MARGIN:.0%} margin.")
    write_report(app, s, rows, material, price)
    print("Wrote out/quote.md")


if __name__ == "__main__":
    main()
