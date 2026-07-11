from tkinter import Tk, filedialog
import mido
import math
import pyperclip
import re


# ------------------------------------
# Configuration
# ------------------------------------

ELEMENTS_PER_BLOCK = 96

# MIDI -> Desmos octave correction
OCTAVE_OFFSET = 1

SHIFT_LOWEST_OCTAVE = True


NOTE_NAMES = [
    "C", "C_sharp", "D", "D_sharp",
    "E", "F", "F_sharp", "G",
    "G_sharp", "A", "A_sharp", "B"
]


# ------------------------------------
# MIDI note -> Desmos note
# ------------------------------------

def midi_to_desmos(note):

    octave = note // 12 - 1 + OCTAVE_OFFSET
    name = NOTE_NAMES[note % 12]

    if "_sharp" in name:
        letter = name.replace("_sharp", "")
        return f"{letter}_{{sharp{octave}}}"

    return f"{name}_{{{octave}}}"



# ------------------------------------
# Shift low note range
# ------------------------------------

def shift_low_octaves(note, lowest_octave, octave_range):

    if not SHIFT_LOWEST_OCTAVE:
        return note


    match = re.search(r"(\d+)", note)

    if not match:
        return note


    octave = int(match.group(1))


    if (
        lowest_octave
        <= octave
        <= lowest_octave + octave_range - 1
    ):

        octave += 1

        note = re.sub(
            r"\d+",
            str(octave),
            note,
            count=1
        )


    return note



# ------------------------------------
# Select MIDI
# ------------------------------------

root = Tk()
root.withdraw()

filename = filedialog.askopenfilename(
    title="Select MIDI File",
    filetypes=[
        ("MIDI Files", "*.mid *.midi")
    ]
)

if not filename:
    quit()


mid = mido.MidiFile(filename)



# ------------------------------------
# Find lowest MIDI note
# ------------------------------------

lowest_midi_note = 999


for track in mid.tracks:

    for msg in track:

        if (
            msg.type == "note_on"
            and msg.velocity > 0
            and not (
                hasattr(msg, "channel")
                and msg.channel == 9
            )
        ):

            lowest_midi_note = min(
                lowest_midi_note,
                msg.note
            )


if lowest_midi_note != 999:

    lowest_octave = (
        lowest_midi_note // 12 - 1
    )

else:

    lowest_octave = 0


print(
    f"\nLowest MIDI note: {lowest_midi_note}"
)

print(
    f"Lowest octave: {lowest_octave}"
)



# ------------------------------------
# Ask octave range
# ------------------------------------

while True:

    try:

        octave_range = int(
            input(
                "How many octaves above the lowest note should be shifted? (0 = none): "
            )
        )

        if octave_range >= 0:
            break


    except ValueError:
        pass


    print(
        "Enter a whole number."
    )



# ------------------------------------
# Detect BPM
# ------------------------------------

tempo = 500000


for track in mid.tracks:

    for msg in track:

        if msg.type == "set_tempo":

            tempo = msg.tempo
            break



midi_bpm = mido.tempo2bpm(tempo)


print(
    f"\nDetected MIDI BPM: {midi_bpm:.2f}"
)



# ------------------------------------
# BPM override
# ------------------------------------

while True:

    bpm_input = input(
        "Enter BPM (press Enter to use MIDI BPM): "
    ).strip()


    if bpm_input == "":

        bpm = midi_bpm
        break


    try:

        bpm = float(bpm_input)

        if bpm > 0:
            break


    except ValueError:
        pass


    print("Invalid BPM.")



# ------------------------------------
# Export amount
# ------------------------------------

while True:

    blocks_input = input(
        "How many 4-measure blocks should be exported? (or type 'all'): "
    ).strip().lower()


    if blocks_input == "all":

        blocks_to_export = None
        break


    try:

        blocks_to_export = int(blocks_input)

        if blocks_to_export > 0:
            break


    except ValueError:
        pass


    print(
        "Enter a positive number or 'all'."
    )



# ------------------------------------
# Read MIDI
# ------------------------------------

ticks_per_step = mid.ticks_per_beat / 6

timeline = {}


for track in mid.tracks:

    absolute_ticks = 0


    for msg in track:

        absolute_ticks += msg.time


        # Ignore drums
        if (
            hasattr(msg, "channel")
            and msg.channel == 9
        ):
            continue


        if (
            msg.type == "note_on"
            and msg.velocity > 0
        ):


            step = round(
                absolute_ticks / ticks_per_step
            )


            if step not in timeline:
                timeline[step] = []


            note = midi_to_desmos(
                msg.note
            )


            note = shift_low_octaves(
                note,
                lowest_octave,
                octave_range
            )


            timeline[step].append(note)



for step in timeline:

    timeline[step].sort(reverse=True)



# ------------------------------------
# Determine blocks
# ------------------------------------

if timeline:

    last_step = max(timeline.keys())

else:

    last_step = 0



total_blocks = math.ceil(
    (last_step + 1)
    / ELEMENTS_PER_BLOCK
)


if blocks_to_export is None:

    num_blocks = total_blocks

else:

    num_blocks = min(
        blocks_to_export,
        total_blocks
    )



# ------------------------------------
# Polyphony per block
# ------------------------------------

block_polyphony = []


for block in range(num_blocks):

    highest = 1


    for step in range(
        block * ELEMENTS_PER_BLOCK,
        (block + 1) * ELEMENTS_PER_BLOCK
    ):

        if step in timeline:

            highest = max(
                highest,
                len(timeline[step])
            )


    block_polyphony.append(highest)



# ------------------------------------
# Generate variables
# ------------------------------------

variables_output = []


for block in range(num_blocks):

    for voice in range(
        block_polyphony[block]
    ):

        elements = []


        for i in range(ELEMENTS_PER_BLOCK):

            step = (
                block * ELEMENTS_PER_BLOCK
                + i
            )


            notes = timeline.get(
                step,
                []
            )


            if voice < len(notes):

                elements.append(
                    notes[voice]
                )

            else:

                elements.append("R")



        variables_output.append(
            f"M_{{{block + 1}{voice + 1:02d}}}"
            "="
            "\\left["
            + ",".join(elements)
            + "\\right]"
        )



pyperclip.copy(
    "\n".join(variables_output)
)


print(
    f"\nCopied {len(variables_output)} variables to clipboard!"
)



# ------------------------------------
# Tone operators
# ------------------------------------

print(
    "\n=== TONE OPERATORS ===\n"
)


for block in range(num_blocks):

    tones = []


    for voice in range(
        block_polyphony[block]
    ):

        if block == 0:

            time = "t"

        else:

            time = f"t-{block}n"



        tones.append(
            f"M_{{{block + 1}{voice + 1:02d}}}"
            f"\\left[{time}\\right]"
        )


    print(
        "\\operatorname{tone}"
        "\\left("
        "\\left["
        + ",".join(tones)
        + "\\right],"
        + str(block_polyphony[block])
        + "\\right)"
    )



# ------------------------------------
# Final timing
# ------------------------------------

quarter_ms = 60000 / bpm
sixteenth_ms = quarter_ms / 4
triplet_ms = quarter_ms / 6


print("\n=== FINAL TIMING ===")

print(f"BPM: {bpm:.2f}")
print(f"Quarter note: {quarter_ms:.2f} ms")
print(f"Sixteenth note: {sixteenth_ms:.2f} ms")
print(f"16th triplet subdivision: {triplet_ms:.2f} ms")


print("\nDone!")