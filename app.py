import json
from pathlib import Path

import gradio as gr
import numpy as np
from PIL import Image
from transformers import pipeline

# ============================================================
# TACTOGRAPH CONFIGURATION
# ============================================================

BOARD_ROWS = 11
BOARD_COLS = 15

MODEL_NAME = "depth-anything/Depth-Anything-V2-Small-hf"

OUTPUT_FILE = Path("depth_map.json")

INVERT_HEIGHTS = False


# ============================================================
# LOAD DEPTH MODEL
# ============================================================

print("Loading Depth Anything V2...")

depth_estimator = pipeline(
    task="depth-estimation",
    model=MODEL_NAME
)

print("Depth model loaded successfully.")


# ============================================================
# DEPTH NORMALIZATION
# ============================================================

def normalize_to_percent(depth_grid):

    depth_grid = depth_grid.astype(np.float32)

    minimum = float(depth_grid.min())
    maximum = float(depth_grid.max())

    if maximum == minimum:
        return np.zeros_like(
            depth_grid,
            dtype=int
        )

    normalized = (
        depth_grid - minimum
    ) / (
        maximum - minimum
    )

    if INVERT_HEIGHTS:
        normalized = 1.0 - normalized

    percentage_grid = normalized * 100

    return np.round(
        percentage_grid,
        0
    ).astype(int)


# ============================================================
# HEATMAP PREVIEW
# ============================================================

def create_heatmap(percentage_grid):

    heatmap = Image.fromarray(
        np.uint8(percentage_grid * 2.55)
    )

    CELL_SIZE = 50

    heatmap = heatmap.resize(
        (
            BOARD_COLS * CELL_SIZE,
            BOARD_ROWS * CELL_SIZE
        ),
        Image.Resampling.NEAREST
    )

    return heatmap

# ============================================================
# DEPTH PROCESSING
# ============================================================

def crop_to_board_ratio(image):

    target_ratio = BOARD_COLS / BOARD_ROWS

    width, height = image.size

    current_ratio = width / height

    if current_ratio > target_ratio:

        # image is too wide
        new_width = int(height * target_ratio)

        left = (width - new_width) // 2

        image = image.crop(
            (
                left,
                0,
                left + new_width,
                height
            )
        )

    else:

        # image is too tall
        new_height = int(width / target_ratio)

        top = (height - new_height) // 2

        image = image.crop(
            (
                0,
                top,
                width,
                top + new_height
            )
        )

    return image


def generate_depth_map(input_image):

    if input_image is None:
        raise gr.Error(
            "Upload an image or take a photo first."
        )

    input_image = input_image.convert("RGB")

    input_image = crop_to_board_ratio(
        input_image
    )
    
    print("Generating depth map...")

    result = depth_estimator(input_image)

    depth_image = result["depth"]

    if not isinstance(depth_image, Image.Image):
        depth_image = Image.fromarray(
            np.asarray(depth_image)
        )

# Physical display:
# 15 columns x 11 rows

# Hardware output:
# 15 gantry positions x 11 servo values

# We transpose after sampling to match the
# physical actuator architecture.


    grid_image = depth_image.resize(
        (BOARD_COLS, BOARD_ROWS),
        Image.Resampling.BILINEAR
    )

    raw_grid = np.asarray(
        grid_image,
        dtype=np.float32
    )

    depth_percentages = normalize_to_percent(
    raw_grid
)
    
    print("\nGenerated Depth Matrix")

    print(depth_percentages)

    print(
        f"\nMatrix Shape: "
        f"{depth_percentages.shape}"
    )

    heatmap_image = create_heatmap(
        depth_percentages
    )

    print_data = {
        "project": "Tactograph",
        "scale": "0_to_100_percent",
        "board_rows": BOARD_ROWS,
        "board_cols": BOARD_COLS,
        "orientation":
            "Visual display grid: 11 outer lists representing rows, "
            "with 15 depth percentages in each row.",
        "depth_percentages":
            depth_percentages.tolist()
    }

    with OUTPUT_FILE.open(
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            print_data,
            file,
            indent=2
        )

    status = (
        f"Depth processing complete. "
        f"Generated {BOARD_COLS} board columns "
        f"with {BOARD_ROWS} board rows. "
        f"Normalized from 0% to 100%."
    )

    return (
        heatmap_image,
        depth_percentages.tolist(),
        str(OUTPUT_FILE),
        status,
        depth_percentages.tolist()
    )


# ============================================================
# PRINT PLACEHOLDER
# ============================================================

import time
from controller import (
    get_controller,
    set_heights,
    reset_heights,
    set_lock,
    advance_stepper,
)

ctrl = get_controller()

def print_on_tactograph(depth_grid):
    if depth_grid is None:
        raise gr.Error("Compute depth before printing.")

    display_grid = np.asarray(depth_grid, dtype=int)

    if display_grid.shape != (BOARD_ROWS, BOARD_COLS):
        raise gr.Error(
            f"Expected a display grid shaped {BOARD_ROWS} × {BOARD_COLS}, "
            f"but received {display_grid.shape}."
        )

    hardware_grid = display_grid.T

    print(hardware_grid)

    try:
        set_lock(1.0)
        for row in hardware_grid:
            set_heights([x / 30.0 for x in row])
            time.sleep(1.2)

            # Retract actuator servos back to home
            reset_heights()
            time.sleep(0.8)

            advance_stepper(1)

    except KeyboardInterrupt:
        print("\n[Print Interrupted] Halting print sequence...")
        cancelled = True
    finally:
        # Guarantee reset on exit or error
        reset_heights()
        set_lock(0.0)

    if cancelled:
        return 
    return (
        "Print sequence generated successfully. "
        "The hardware matrix is ready for transmission."
    )


def reset_pin_board():

    print("\n================================")
    print("TACTOGRAPH RESET")
    print("================================")

    print("Activating reset servo...")
    print("Activating reset stepper...")
    print("Clearing tactile surface...")
    print("Reset complete.")

    return (
        "Tactile surface reset successfully."
    )

# ============================================================
# USER INTERFACE
# ============================================================

with gr.Blocks(
    title="Tactograph"
) as demo:

    # Logo

    with gr.Row():
        gr.Image(
            value=Path("C:\\Users\\jaden\\OneDrive\\Desktop\\Tactography\\logo.png"),
            show_label=False,
            interactive=False,
            container=False,
            height=220
        )

    # Instructions

    gr.Markdown("""
## Welcome to Tactograph

### Getting Started

1. Upload an image or take a live photo.
2. Click **Compute Depth**.
3. Review the generated tactile heatmap.
4. Click **Print on Tactograph**.
5. Download the generated print instructions.

The display is sampled onto an **11-row × 15-column tactile grid** and normalized to **0%–100% depth values**.
""")

    stored_depth_grid = gr.State(
        value=None
    )

    with gr.Row():

        input_image = gr.Image(
            label="Input Image",
            sources=["upload", "webcam"],
            type="pil"
        )

        depth_output = gr.Image(
            label="Tactograph Heatmap Preview",
            type="pil"
        )

    with gr.Row():

        compute_button = gr.Button(
            "Compute Depth",
            variant="primary"
        )

        print_button = gr.Button(
            "Print on Tactograph"
        )

        reset_button = gr.Button(
            "Reset Tactile Surface"
        )

    status_output = gr.Textbox(
        label="Status",
        interactive=False
    )

    depth_output_json = gr.JSON(
        label="Depth Percentages (0–100)"
    )

    file_output = gr.File(
        label="Download Print Instructions"
    )

    compute_button.click(
        fn=generate_depth_map,
        inputs=input_image,
        outputs=[
            depth_output,
            depth_output_json,
            file_output,
            status_output,
            stored_depth_grid
        ]
    )

    print_button.click(
        fn=print_on_tactograph,
        inputs=stored_depth_grid,
        outputs=status_output
    )

    reset_button.click(
        fn=reset_pin_board,
        outputs=status_output
    )


if __name__ == "__main__":

    print("Launching Gradio...")

    demo.launch(
        debug=True
    )
