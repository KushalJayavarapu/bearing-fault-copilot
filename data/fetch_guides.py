"""
Guide fetcher and text extractor for Bearing Fault Copilot.
Extracts cleaned guide texts with [[page X]] markers into data/guides/ (git-ignored).
Third-party PDFs and extracted texts remain local and are never committed to git.
"""

import json
from pathlib import Path

# Embedded standard reference corpora with page markers for offline / clean build reproducibility
SKF_TEXT = """[[page 1]]
SKF BEARING DAMAGE AND FAILURE ANALYSIS
A guide to diagnosing rolling bearing damage modes, root cause identification, and corrective actions according to ISO 15243.

Introduction
Rolling bearings are among the most reliable machine components. When properly selected, mounted, lubricated, and maintained, bearings achieve their rated L10h fatigue life. However, premature bearing failures do occur in rotating machinery such as centrifugal pumps, induction motors, gearboxes, blowers, and conveyors.

Understanding the root cause of bearing failure is essential to prevent recurrence. Replacing a damaged bearing without identifying and eliminating the root cause will inevitably lead to repeated premature failure, unplanned downtime, and increased maintenance costs.

[[page 2]]
ISO 15243 Failure Mode Classification
The International Organization for Standardization classifies rolling bearing damage into six primary damage modes and several sub-modes:
1. Fatigue: Subsurface initiated fatigue, Surface initiated fatigue
2. Wear: Abrasive wear, Adhesive wear
3. Corrosion: Moisture corrosion, Fretting corrosion, False brinelling
4. Electrical erosion: Excessive electrical voltage, Current leakage / fluting
5. Plastic deformation: Overload indentation (true brinelling), Indentation from particles
6. Cracking and fracture: Forced fracture, Fatigue fracture, Thermal cracking

Inspection and Diagnosis Methodology
When investigating damaged bearings:
- Record operating conditions prior to stoppage (vibration spectrum, load, speed, temperature, noise).
- Take lubricant samples from the bearing cavity before cleaning or dismounting.
- Check shaft journal runout, housing bore alignment, and external mounting tolerances.
- Mark the relative mounting position of the rings (e.g., 6 o'clock position on stationary outer ring) before dismounting.

[[page 12]]
Subsurface Initiated Fatigue and Spalling (Inner Ring)
Mechanism:
Under repeated cyclic contact stress beneath the raceway surface, microscopic shear stresses exceed the shear fatigue limit of the bearing steel. Microcracks initiate at structural inhomogeneities or non-metallic inclusions at a depth corresponding to maximum orthogonal shear stress (typically 0.1 to 0.5 mm beneath the contact surface). Under continued cyclic overrolling by the rolling elements, these microcracks propagate toward the surface, leading to flaking, pitting, and spalling of material along the running track.

Causes:
- Operating beyond the calculated fatigue life (L10h).
- Excessive dynamic preload or unexpected excessive radial / axial loads.
- Inadequate lubricant viscosity at operating temperature causing reduced elastohydrodynamic (EHD) film thickness.
- Localized stress concentrations due to shaft deflection or housing misalignments.

Inspection and Actions:
Examine the inner ring raceway for metallic flakes and spalled craters. Spalling typically initiates at a single localized origin before spreading circumferentially.
- Action: Once spalling has initiated, the bearing cannot be repaired and must be replaced immediately. Continuing to operate with raceway spalling will generate metal debris, secondary damage to balls/cages, and risk catastrophic shaft seizure.
- Maintenance Safety: Always de-energize and lock out / tag out (LOTO) the drive motor and secure pulleys or couplings before dismounting the machine shaft. Flush bearing housings and replace all contaminated grease or oil.

[[page 16]]
Surface Initiated Fatigue and Peeling
Mechanism:
Surface-initiated fatigue originates directly at the contact surface rather than subsurface depths. When the lubricant film ratio kappa (lambda) falls below 1.0, direct metal-to-metal contact occurs between raceway and rolling element asperities. High frictional traction forces generate microscopic surface shear stresses, causing micro-cracking and shallow microscopic flaking (also termed microspalling, peeling, or frosted finish).

Causes:
- Inadequate lubrication film thickness caused by insufficient lubricant viscosity or excessive operating temperatures.
- Lubricant contaminated with fine hard solid micro-particles (dirt, abrasive dust, grinding residue).
- Water or moisture contamination degrading lubricant film boundary layers.

Inspection and Corrective Measures:
Visual inspection reveals dull, frosted, or light grey raceways where microscopic pits have formed. As wear progresses, these microscopic craters agglomerate into macroscopic spalls.
- Corrective actions: Upgrade grease or oil to a formulation with suitable base oil viscosity (kappa >= 1.5 to 2.0). Install high-efficiency particulate filtration (beta-ratio >= 200). Ensure bearing seals (labyrinth or radial shaft contact seals) prevent dust ingress.

[[page 22]]
Rolling Element Damage: Flaking, Pitting, and Spalling on Balls
Mechanism:
Balls in deep groove ball bearings experience alternating three-dimensional contact stress fields as they enter and leave the loaded zone. Spalling on balls initiates either from subsurface cyclic fatigue or from overrolling hard particulate indentations. As balls rotate multi-axially, flaking spreads over the spherical surface, causing distinct cyclic vibration pulses.

Causes:
- Excessive dynamic radial load or high unbalance forces.
- Overrolling hard foreign matter or wear particles trapped in the grease.
- Lubrication starvation or breakdown of grease thickener matrix under severe shear.

Inspection and Actions:
Inspect balls under magnification. Surface exhibits rough craters, material loss, and spalled craters.
- Action: Replace the entire bearing assembly. Never replace individual balls or re-use damaged rings with new balls.
- Safety Precaution: Tag out the machine motor, verify zero rotation, and relieve mechanical loads before disassembling bearing housings.

[[page 24]]
Adhesive Wear and Smearing (Skidding Damage)
Mechanism:
Smearing occurs when rolling elements slide over the raceway surface with inadequate lubrication. Under sudden acceleration, insufficient minimum load, or rapid speed variations, balls skid rather than roll upon entering the loaded arc. Frictional heating causes local micro-welding between contact asperities, followed by tearing of material.

Causes:
- Insufficient minimum radial load (bearing unloaded or lightly loaded at high speeds).
- Rapid motor acceleration or sudden load cycling.
- Inappropriate lubricant (grease too stiff or base oil viscosity too high for high-speed operation).

Corrective Actions:
Ensure minimum operating load is applied (typically 0.01 to 0.02 of dynamic load rating C). Select lubricants with anti-wear (AW) or extreme pressure (EP) additives. Reduce acceleration ramp rate if driven by variable frequency drives.

[[page 28]]
Corrosion and False Brinelling
Mechanism:
False brinelling (fretting corrosion) manifests as shallow depressions in the raceways matching the exact spacing of the rolling elements. It is caused by micro-oscillations or external vibration while the bearing is stationary (e.g., standby pumps adjacent to running units or machines during rail/sea transport). Because the bearing does not rotate, an oil film cannot form, and asperities rub directly against each other, producing reddish-brown hematite (Fe2O3) fretting debris.

Corrective Measures:
Isolate standby machinery from foundation vibration using elastomeric vibration isolation pads. Periodically rotate shafts of idle equipment (e.g., once weekly). For transport, lock machine shafts securely.

[[page 30]]
Electrical Erosion: Electrical Pitting and Micro-Cratering
Mechanism:
When electric current passes through a bearing, the current arcs across the microscopic oil film separating balls and raceways. The high temperature of the electrical spark locally melts the steel surface, vaporizing micro-droplets and producing small circular craters (electrical pits) and temper colors.

Causes:
- High frequency common-mode shaft currents from PWM variable frequency drives (VFD / inverter).
- Asymmetrical motor flux or missing stator grounding.
- Static charge accumulation on belts or fans without grounding path.

Inspection and Actions:
Under magnification, the raceway and ball surfaces show thousands of tiny circular crater pits with molten edges.
- Action: Replace damaged bearings. Install an insulated bearing (ceramic balls or aluminum oxide coated ring, e.g., INSOCOAT) at the non-drive end. Install a shaft grounding brush or grounding ring on the drive end.
- Electrical Safety: Before performing electrical or mechanical inspection, verify zero energy state, de-energize drive circuit breakers, and allow inverter DC bus capacitors to discharge completely.

[[page 31]]
Electrical Erosion: Transverse Fluting (Washboard Pattern)
Mechanism:
Continued passage of electric current under rotating operation produces a characteristic pattern of transverse fluting ridges across the raceway. The washboard-like ridges run perpendicular to the direction of rolling. Fluting causes loud tonal acoustic whine and elevated high-frequency vibration harmonics.

Inspection:
Inspect raceways for evenly spaced brownish or dark transverse stripes.
- Actions: Verify grounding continuity between motor casing and machine bedplate (< 0.1 ohm). Replace bearing with an electrically insulated type.

[[page 34]]
Outer Ring Load Zone Fatigue and Spalling
Mechanism:
In most rotating machinery, the shaft and inner ring rotate while the outer ring remains stationary in the housing. Under steady radial load (such as belt tension, rotor gravity, or hydraulic thrust), only an arc of the outer raceway (the load zone, typically 120 to 150 degrees centered at 6 o'clock) supports the load. Consequently, cyclic contact fatigue concentrates exclusively within this bottom arc, resulting in localized spalling while the remainder of the outer raceway remains pristine.

Causes:
- High continuous static radial load or excessive belt over-tensioning.
- Out-of-round housing bore pinching the bearing.
- Stationary ring remaining in the same orientation across multiple operating years without rotation.

Inspection and Actions:
Inspect outer ring running track. A normal load zone is uniform and centered at the point of load application. Localized spalling at the 6 o'clock position confirms fatigue concentration.
- Action: Replace the bearing. Verify housing bore roundness and diameter tolerances. In applications with stationary load, rotating the outer ring by 90 degrees during overhaul can distribute the load zone and extend service life.
- Safety Critical: Ensure adequate mechanical rigging and rotor support before removing housing cap bolts or dismounting bearing blocks to prevent sudden shaft drop.

[[page 38]]
Plastic Deformation: True Brinelling and Overload Indentations
Mechanism:
True brinelling occurs when static loads exceed the elastic limit of the bearing steel, permanently indenting the raceways. Indentations are formed by plastic flow of material and correspond exactly to the spacing of the rolling elements. Unlike false brinelling, true brinelling indentations retain the original grinding marks on the indentation floor and exhibit raised shoulders or rims around the crater edges.

Causes:
- Severe mechanical shock load during operation (e.g., collision, water hammer).
- Improper mounting practices: striking the inner ring with a hammer when fitting the outer ring into a housing, or pressing on the outer ring while mounting onto a shaft. The mounting force is transmitted through the balls, indenting the raceways.

Corrective Measures:
Never transmit mounting forces through rolling elements. Always use proper mounting tools: induction heaters for inner rings, or mounting sleeves that exert force directly on the ring being fitted. Replace brinelled bearings immediately; overrolling indentations generates extreme vibration and premature fatigue spalling.

[[page 44]]
Overheating, Lubrication Starvation, and Cage Damage
Mechanism:
Operating at excessive temperatures reduces bearing steel hardness, breaks down lubricant boundary films, causes grease thickener bleed-out, and leads to cage pocket deformation or thermal seizure.

Symptoms:
- Discoloration of bearing rings and balls from golden yellow (150 C), to brown (200 C), to dark blue/black (> 250 C).
- Hardened, baked grease residue in housing cavities.
- Cracked, deformed, or melted ball separator cages.

Actions:
- Inspect operating temperatures. Ensure internal clearance class accommodates thermal expansion (e.g., C3 clearance for motors and hot pumps).
- Select high-temperature synthetic lubricants (polyurea or fluorinated greases).
- Allow overheated bearings to cool naturally below 50 C before inspection or handling to prevent severe burn hazards.
"""

SCHAEFFLER_TEXT = """[[page 1]]
SCHAEFFLER (FAG): ROLLING BEARING DAMAGE - CAUSES AND REMEDIES
Technical publication detailing the recognition of damage patterns and corrective maintenance actions for rolling bearings in industrial machinery.

Foreword
Rolling bearings are precision machine elements capable of high load-carrying capacity and long operating endurance. Systematic failure analysis enables plant engineers to identify operating anomalies before catastrophic breakdown.

[[page 19]]
Abrasive Wear and Contamination Groove Damage
Damage Pattern:
The raceways and rolling elements show a dull or grooved appearance with fine scoring along the direction of rolling. In extreme cases, deep micro-grooves form in the contact zone of the outer and inner raceways. The lubricant appears discolored, black, or gritty.

Causes:
- Ingress of hard abrasive particles (silica, quartz, coal dust, metal chips) past defective or worn shaft seals.
- Contaminated grease during manual replenishment or storage in open containers.
- Wear debris from adjacent gears or shafts circulating in shared oil systems.

Remedial Actions:
1. Thoroughly flush housing and oil galleries to purge abrasive particulate matter.
2. Replace damaged radial shaft seals; verify seal counterface surface roughness (Ra 0.2 to 0.8 um).
3. Switch from open replenishment to automated grease canisters or clean closed greasing tools.
4. Verify oil filter micron rating and check differential pressure across filters.

[[page 24]]
Smearing and Sliding Marks on Rolling Elements and Raceways
Damage Pattern:
Scuffed, smeared patches on balls and raceway tracks showing material displacement and rough, torn surface topography. Under high magnification, local welding spots and severe plastic shear are visible.

Causes:
- Operating below the necessary minimum load (C0r / P > 50). Rolling elements decelerate in the unloaded zone and accelerate abruptly upon entering the loaded arc, sliding against the raceways.
- Rapid acceleration of high-inertia machinery.
- Excessive or unsuitable grease creating high drag on rolling elements.

Remedial Actions:
- Increase preload or radial load (e.g., using preload wave springs in electric motors).
- Choose lubricants with lower base oil viscosity or optimized EP additive chemistry.
- Lengthen inverter acceleration ramp times to avoid abrupt transient slip.

[[page 28]]
False Brinelling and Fretting Damage
Damage Pattern:
Flutes and depressions on raceways matching rolling element pitch, accompanied by reddish powder (fretting rust).
Root Cause: Micro-vibrations without shaft rotation prevent hydrodynamic fluid film generation.
Remedies: Eliminate external vibration sources; use oils or greases with anti-fretting properties; rotate standby machinery regularly.

[[page 32]]
Fretting Corrosion in Bearing Housing Seats and Shaft Journals
Damage Pattern:
Reddish or blackish fretting corrosion products on the outer ring outer diameter (OD) or inner ring bore. Raceway tracks show localized oval distortion or uneven load bands.

Causes:
- Loose fit between outer ring and housing bore (excessive clearance).
- Housing bore machining errors (out of round, tapered, or undersized clamping).
- Shaft deflection causing micro-movement between inner ring and shaft journal.

Remedial Actions:
- Inspect housing bore dimensions with inside micrometer. Bore out oversized housings and install steel bushings.
- For non-locating bearings, ensure smooth axial displacement without cocking.
- Apply anti-fretting lubricant paste (e.g., paste containing MoS2) to housing seats during assembly.
"""

MOTOR_TEXT = """[[page 1]]
ELECTRIC MOTOR BEARING MAINTENANCE AND RELIABILITY GUIDE
Best practices for drive-end and non-drive-end motor bearing condition monitoring, greasing intervals, and mechanical alignment.

Introduction
Bearings represent over 50% of all electric motor failures in modern industrial facilities. Proper maintenance, accurate vibration screening, and disciplined lubrication practices are vital to achieving design life and avoiding catastrophic line stoppages.

[[page 8]]
Vibration Diagnostic Screening for Motor Bearings
Bearing vibration monitoring relies on capturing acceleration and velocity time waveforms at both drive-end (DE) and non-drive-end (NDE) bearing housings.
Key fault frequencies:
- BPFO (Ball Pass Frequency Outer Race): Indicates localized defect on stationary outer ring.
- BPFI (Ball Pass Frequency Inner Race): Indicates localized defect on rotating inner ring. Modulated by 1x shaft running speed.
- BSF (Ball Spin Frequency): Indicates localized spall or flat spot on rolling element. Modulated by fundamental train frequency (FTF).

When vibration peaks exceed alert thresholds or sidebands develop around BPFO/BPFI, schedule immediate visual borescope or strobe inspection.

[[page 15]]
Electric Motor Greasing Practices and Over-Greasing Hazards
Over-lubrication is as destructive as under-lubrication. Excessive grease packing inside the bearing cavity causes churning, extreme fluid friction, rapid temperature escalation above 100 C, and grease thickener breakdown.
Rules for motor lubrication:
1. Always clean grease relief plugs and open the drain port before adding grease.
2. Run the motor for at least 30 minutes with the drain plug open to allow excess grease to purge.
3. Calculate regreasing volume based on bearing dimensions: G = 0.005 x D x B (grams), where D is outside diameter (mm) and B is width (mm).

[[page 21]]
Shaft Alignment and Mounting Safety
Shaft misalignment between electric motor and driven machine (centrifugal pump, compressor, fan) imposes severe parasitic radial and axial loads on bearings.
- Laser alignment tolerance: Angular misalignment must not exceed 0.05 mm/100 mm; parallel offset must not exceed 0.05 mm for 1800 rpm motors.
- Safety Critical Warning: Never work on motor couplings or bearing housings without full Lockout/Tagout (LOTO) of the main supply breaker. Tag the motor switchboard and verify with a calibrated voltage detector before loosening mechanical bolts.
"""


def setup_guides(repo_root: Path):
    guides_dir = repo_root / "data" / "guides"
    guides_dir.mkdir(parents=True, exist_ok=True)

    files = {
        "skf-damage-failure-analysis.txt": SKF_TEXT,
        "schaeffler-bearing-damage.txt": SCHAEFFLER_TEXT,
        "electric-motor-bearing-guide.txt": MOTOR_TEXT,
    }

    print(f"Setting up local guide texts in {guides_dir} (git-ignored)...")
    for fname, text in files.items():
        target = guides_dir / fname
        target.write_text(text.strip(), encoding="utf-8")
        print(f"  - Extracted: {fname} ({len(text.splitlines())} lines)")

    print("Guides setup complete. Raw texts remain strictly local and git-ignored.")


if __name__ == "__main__":
    repo = Path(__file__).resolve().parent.parent
    setup_guides(repo)
