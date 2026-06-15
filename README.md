# Ember: industrial electric heater sizing and quoting

What does an application engineer at a process-heating company actually do with a
customer enquiry? Take "I need to heat this much fluid to this temperature in this much
time," turn it into a heater that's correctly sized and safe for the fluid, and quote it.
Ember is a small, working model of that, end to end.

## What it does
Given a heating application, Ember:
- **Sizes the power.** Sensible heat to raise the fluid (Q = m·cp·dT), the power to do it
  in the required heat-up time, plus standby loss to hold temperature, with a safety factor.
- **Checks watt density.** The real constraint in heater sizing usually isn't total power,
  it's W/in² on the element sheath. Push it too high and the fluid film overheats (oils
  coke, water scales). Ember spreads the power across enough elements to stay under the
  fluid's limit, which is why an oil heater needs many low-density elements.
- **Picks a standard rating** from a catalog and the element count.
- **Builds a bill of materials and a quote**, material cost plus margin.

It writes a full sizing-and-quote report to `out/quote.md` and a sizing chart to
`out/sizing.png`.

## Worked example (the default run)
Heat 200 gallons of heat-transfer oil from 20 to 150 C in two hours, then hold it. Ember
sizes about 28 kW, selects a 30 kW heater, and spreads it across enough elements to keep
watt density under the 18 W/in² limit for oil, then quotes the assembly. Run it and read
`out/quote.md` for the full breakdown.

## Run it 
```bash
pip install -r requirements.txt   # only needed for the chart; the sizing runs on stdlib
python ember.py
```

## Engineering basis and references
- Sensible heat and heat loss: standard heat-transfer fundamentals (Incropera, *Fundamentals
  of Heat and Mass Transfer*).
- Watt-density limits by fluid: industry heater-sizing guidance (Chromalox and Watlow
  application guides). The limits here are representative, water tolerates high watt
  density, oils much less.

## Limitations
The fluid properties and watt-density limits are representative values, and the price list
is illustrative, not a real catalog. Standby loss is entered as a lumped UA rather than
modeled from tank geometry and insulation. The point is the method an application engineer
follows: size for power, constrain by watt density, then build the BOM and quote.
