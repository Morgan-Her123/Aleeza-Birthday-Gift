import os
import random
from fractions import Fraction
import tkinter as tk

GRID_W = 20
GRID_H = 20
BASE_VISION_RADIUS = 2
ANOMALIES = 6
BASE_PROVISIONS = 38

BG_UNKNOWN = "#0a0f1a"
GRID_LINE = "#1f2937"
ANOMALY_COLOR = "#f9a826"
SHIP_COLOR = "#7ee7ff"

MAP_FILE = "world_map1.png"

EXPLORERS = {
    "Zheng He": {
        "quote": "The compass and the stars agree. We press onward.",
        "vision_bonus": 1,
        "provisions_bonus": -6,
        "cartography_bonus": 0,
        "anomaly_sense": 0,
        "flaw": "Expansive fleet, heavy supplies.",
    },
    "Ferdinand Magellan": {
        "quote": "The horizon yields when we dare to cross it.",
        "vision_bonus": -1,
        "provisions_bonus": 8,
        "cartography_bonus": 0,
        "anomaly_sense": 0,
        "flaw": "Stubborn route, narrower sight.",
    },
    "James Cook": {
        "quote": "We chart what we can, and respect what we cannot.",
        "vision_bonus": 0,
        "provisions_bonus": 2,
        "cartography_bonus": 1,
        "anomaly_sense": 0,
        "flaw": "Measured pace, modest reach.",
    },
    "Christopher Columbus": {
        "quote": "Westward, then. The sea will answer.",
        "vision_bonus": 0,
        "provisions_bonus": -4,
        "cartography_bonus": 0,
        "anomaly_sense": 1,
        "flaw": "Bold guesswork, thin stores.",
    },
}

class StarshipGame:
    def __init__(self, root):
        self.root = root
        self.root.title("Starship Explorer: Age of Discovery")
        self.frame = tk.Frame(root)
        self.frame.pack(padx=8, pady=8)

        self.base_map = self._load_map()
        self.view_box = (0, 0, self.base_map.width(), self.base_map.height())
        self.view_map = self._make_view_image(self.view_box)
        self.full_w = self.base_map.width()
        self.full_h = self.base_map.height()
        self.zoom_w = self.view_map.width()
        self.zoom_h = self.view_map.height()

        self.map_canvas = tk.Canvas(
            self.frame,
            width=self.full_w,
            height=self.full_h,
            bg=BG_UNKNOWN,
            highlightthickness=0,
        )
        self.map_canvas.grid(row=0, column=0, rowspan=2, padx=(0, 10))

        self.zoom_label = tk.Label(self.frame, text="Zoom View", font=("Helvetica", 12, "bold"))
        self.zoom_label.grid(row=0, column=1, sticky="nw")
        self.zoom_canvas = tk.Canvas(
            self.frame,
            width=self.zoom_w,
            height=self.zoom_h,
            bg=BG_UNKNOWN,
            highlightthickness=0,
        )
        self.zoom_canvas.grid(row=1, column=1, sticky="nw")

        self.log_label = tk.Label(self.frame, text="Captain's Log", font=("Helvetica", 12, "bold"))
        self.log_label.grid(row=0, column=2, sticky="nw")
        self.log = tk.Text(self.frame, width=34, height=20, font=("Helvetica", 10), wrap="word", state="disabled")
        self.log.grid(row=1, column=2, sticky="nw")

        self.status = tk.StringVar()
        self.status_label = tk.Label(root, textvariable=self.status, font=("Helvetica", 12))
        self.status_label.pack(pady=(2, 8))

        self.ship = [GRID_W // 2, GRID_H // 2]
        self.discovered = set()
        self.anomalies = set()
        self.discovered_anomalies = set()
        self.explorer = None
        self.vision_radius = BASE_VISION_RADIUS
        self.provisions = BASE_PROVISIONS
        self.game_over = False

        self._place_anomalies()
        self._reveal(self.ship[0], self.ship[1], BASE_VISION_RADIUS)

        self.root.bind("<Up>", lambda e: self.move(0, -1))
        self.root.bind("<Down>", lambda e: self.move(0, 1))
        self.root.bind("<Left>", lambda e: self.move(-1, 0))
        self.root.bind("<Right>", lambda e: self.move(1, 0))
        self.root.bind("w", lambda e: self.move(0, -1))
        self.root.bind("s", lambda e: self.move(0, 1))
        self.root.bind("a", lambda e: self.move(-1, 0))
        self.root.bind("d", lambda e: self.move(1, 0))
        self.root.bind("1", lambda e: self.choose_explorer("Zheng He"))
        self.root.bind("2", lambda e: self.choose_explorer("Ferdinand Magellan"))
        self.root.bind("3", lambda e: self.choose_explorer("James Cook"))
        self.root.bind("4", lambda e: self.choose_explorer("Christopher Columbus"))
        self.root.bind("r", lambda e: self.restart())

        self._log("Select your explorer (1-4) to begin the voyage.")
        self.draw()

    def _load_map(self):
        path = os.path.join(os.path.dirname(__file__), MAP_FILE)
        if not os.path.exists(path):
            raise FileNotFoundError(
                f"Map image not found: {path}. Place {MAP_FILE} in the project folder."
            )
        return tk.PhotoImage(file=path)

    def _make_view_image(self, view_box):
        x0, y0, x1, y1 = view_box
        width = max(1, int(x1 - x0))
        height = max(1, int(y1 - y0))
        crop = tk.PhotoImage(width=width, height=height)
        crop.tk.call(
            crop,
            "copy",
            self.base_map,
            "-from",
            int(x0),
            int(y0),
            int(x1),
            int(y1),
            "-to",
            0,
            0,
        )

        fx = Fraction(self.base_map.width(), width).limit_denominator(16)
        fy = Fraction(self.base_map.height(), height).limit_denominator(16)
        scaled = crop.zoom(fx.numerator, fy.numerator).subsample(fx.denominator, fy.denominator)
        return scaled

    def _place_anomalies(self):
        while len(self.anomalies) < ANOMALIES:
            x = random.randrange(GRID_W)
            y = random.randrange(GRID_H)
            if (x, y) != tuple(self.ship):
                self.anomalies.add((x, y))

    def _reveal(self, cx, cy, radius):
        for y in range(cy - radius, cy + radius + 1):
            for x in range(cx - radius, cx + radius + 1):
                if 0 <= x < GRID_W and 0 <= y < GRID_H:
                    self.discovered.add((x, y))

    def move(self, dx, dy):
        if self.explorer is None or self.game_over:
            return
        nx = self.ship[0] + dx
        ny = self.ship[1] + dy
        if 0 <= nx < GRID_W and 0 <= ny < GRID_H:
            self.ship = [nx, ny]
            self.provisions -= 1
            self._reveal(nx, ny, self.vision_radius)
            if self.explorer["cartography_bonus"]:
                if random.random() < 0.35:
                    self._reveal(nx, ny, self.vision_radius + self.explorer["cartography_bonus"])
            self._check_anomaly(nx, ny)
            if self.provisions <= 0:
                self.game_over = True
            self.draw()

    def draw(self):
        self.map_canvas.delete("all")
        self.map_canvas.create_image(0, 0, anchor="nw", image=self.base_map)
        self.zoom_canvas.delete("all")
        self.zoom_canvas.create_image(0, 0, anchor="nw", image=self.view_map)
        found = 0
        for y in range(GRID_H):
            for x in range(GRID_W):
                mx0, my0, mx1, my1 = self._cell_to_map_rect(x, y)
                fx0, fy0, fx1, fy1 = self._map_rect_to_canvas_full(mx0, my0, mx1, my1)
                zx0, zy0, zx1, zy1 = self._map_rect_to_canvas_zoom(mx0, my0, mx1, my1)

                if (x, y) in self.discovered:
                    self.map_canvas.create_rectangle(fx0, fy0, fx1, fy1, outline=GRID_LINE)
                    if self._rect_in_zoom(zx0, zy0, zx1, zy1):
                        self.zoom_canvas.create_rectangle(zx0, zy0, zx1, zy1, outline=GRID_LINE)
                    if (x, y) in self.anomalies:
                        found += 1
                        ax = (fx0 + fx1) * 0.5
                        ay = (fy0 + fy1) * 0.5
                        self.map_canvas.create_oval(ax - 4, ay - 4, ax + 4, ay + 4, fill=ANOMALY_COLOR, outline="")
                        if self._rect_in_zoom(zx0, zy0, zx1, zy1):
                            zx = (zx0 + zx1) * 0.5
                            zy = (zy0 + zy1) * 0.5
                            self.zoom_canvas.create_oval(zx - 4, zy - 4, zx + 4, zy + 4, fill=ANOMALY_COLOR, outline="")
                else:
                    self.map_canvas.create_rectangle(
                        fx0,
                        fy0,
                        fx1,
                        fy1,
                        fill=BG_UNKNOWN,
                        stipple="gray50",
                        outline=GRID_LINE,
                    )
                    if self._rect_in_zoom(zx0, zy0, zx1, zy1):
                        self.zoom_canvas.create_rectangle(
                            zx0,
                            zy0,
                            zx1,
                            zy1,
                            fill=BG_UNKNOWN,
                            stipple="gray50",
                            outline=GRID_LINE,
                        )

        self._draw_ship()

        if self.explorer is None:
            self.status.set("Choose explorer: 1 Zheng He, 2 Magellan, 3 Cook, 4 Columbus")
        else:
            self.status.set(
                f"{self.explorer_name} | Provisions: {self.provisions} | Anomalies: {found}/{ANOMALIES} | R to restart"
            )

        if found == ANOMALIES:
            self.canvas.create_text(
                GRID_W * TILE // 2,
                GRID_H * TILE // 2,
                text="Sector fully explored!",
                fill="#e5f2ff",
                font=("Helvetica", 18, "bold"),
            )
        elif self.game_over:
            self.canvas.create_text(
                GRID_W * TILE // 2,
                GRID_H * TILE // 2,
                text="Provisions spent. Expedition failed.",
                fill="#f5c2c2",
                font=("Helvetica", 16, "bold"),
            )

    def _draw_ship(self):
        x, y = self.ship
        mx0, my0, mx1, my1 = self._cell_to_map_rect(x, y)
        fx, fy = self._map_point_to_canvas_full((mx0 + mx1) * 0.5, (my0 + my1) * 0.5)
        zx, zy = self._map_point_to_canvas_zoom((mx0 + mx1) * 0.5, (my0 + my1) * 0.5)
        points = [
            (fx, fy - 6),
            (fx - 5, fy + 5),
            (fx + 5, fy + 5),
        ]
        self.map_canvas.create_polygon(points, fill=SHIP_COLOR, outline="")
        if self._point_in_zoom(zx, zy):
            zpoints = [
                (zx, zy - 6),
                (zx - 5, zy + 5),
                (zx + 5, zy + 5),
            ]
            self.zoom_canvas.create_polygon(zpoints, fill=SHIP_COLOR, outline="")

    def _check_anomaly(self, x, y):
        if (x, y) in self.anomalies and (x, y) not in self.discovered_anomalies:
            self.discovered_anomalies.add((x, y))
            bonus = 6
            self.provisions += bonus
            self._log(
                f"Anomaly discovered at {x+1},{y+1}. Supplies recovered (+{bonus})."
            )
        if self.explorer and self.explorer["anomaly_sense"]:
            self._sense_anomaly(x, y)

    def _sense_anomaly(self, x, y):
        for dy in range(-1, 2):
            for dx in range(-1, 2):
                tx = x + dx
                ty = y + dy
                if (tx, ty) in self.anomalies and (tx, ty) not in self.discovered:
                    self._reveal(tx, ty, 0)

    def choose_explorer(self, name):
        if self.explorer is not None:
            return
        self.explorer_name = name
        self.explorer = EXPLORERS[name]
        self.vision_radius = BASE_VISION_RADIUS + self.explorer["vision_bonus"]
        self.provisions = BASE_PROVISIONS + self.explorer["provisions_bonus"]
        self._apply_explorer_view(name)
        self._log(f"Captain selected: {name}.")
        self._log(f"Strengths/Weaknesses: {self.explorer['flaw']}")
        self._log(self.explorer["quote"])
        self.draw()

    def restart(self):
        self.ship = [GRID_W // 2, GRID_H // 2]
        self.discovered = set()
        self.anomalies = set()
        self.discovered_anomalies = set()
        self.explorer = None
        self.explorer_name = ""
        self.vision_radius = BASE_VISION_RADIUS
        self.provisions = BASE_PROVISIONS
        self.game_over = False
        self._place_anomalies()
        self._reveal(self.ship[0], self.ship[1], BASE_VISION_RADIUS)
        self._apply_full_view()
        self._log("New expedition. Select your explorer (1-4).")
        self.draw()

    def _apply_full_view(self):
        self.view_box = (0, 0, self.base_map.width(), self.base_map.height())
        self._apply_view_box()

    def _apply_explorer_view(self, name):
        width = self.base_map.width()
        height = self.base_map.height()
        boxes = {
            "Zheng He": (0.60, 0.28, 0.82, 0.55),
            "Ferdinand Magellan": (0.28, 0.45, 0.58, 0.78),
            "James Cook": (0.70, 0.58, 0.95, 0.90),
            "Christopher Columbus": (0.22, 0.30, 0.48, 0.60),
        }
        if name not in boxes:
            self._apply_full_view()
            return
        x0, y0, x1, y1 = boxes[name]
        self.view_box = (width * x0, height * y0, width * x1, height * y1)
        self._apply_view_box()

    def _apply_view_box(self):
        self.view_map = self._make_view_image(self.view_box)
        self.zoom_w = self.view_map.width()
        self.zoom_h = self.view_map.height()
        self.zoom_canvas.config(width=self.zoom_w, height=self.zoom_h)

    def _cell_to_map_rect(self, x, y):
        width = self.base_map.width()
        height = self.base_map.height()
        mx0 = x * width / GRID_W
        my0 = y * height / GRID_H
        mx1 = (x + 1) * width / GRID_W
        my1 = (y + 1) * height / GRID_H
        return mx0, my0, mx1, my1

    def _map_rect_to_canvas_full(self, mx0, my0, mx1, my1):
        x0, y0 = self._map_point_to_canvas_full(mx0, my0)
        x1, y1 = self._map_point_to_canvas_full(mx1, my1)
        return x0, y0, x1, y1

    def _map_rect_to_canvas_zoom(self, mx0, my0, mx1, my1):
        x0, y0 = self._map_point_to_canvas_zoom(mx0, my0)
        x1, y1 = self._map_point_to_canvas_zoom(mx1, my1)
        return x0, y0, x1, y1

    def _map_point_to_canvas_full(self, mx, my):
        width = self.base_map.width()
        height = self.base_map.height()
        return mx * self.full_w / width, my * self.full_h / height

    def _map_point_to_canvas_zoom(self, mx, my):
        vx0, vy0, vx1, vy1 = self.view_box
        view_w = max(1.0, vx1 - vx0)
        view_h = max(1.0, vy1 - vy0)
        sx = (mx - vx0) * self.zoom_w / view_w
        sy = (my - vy0) * self.zoom_h / view_h
        return sx, sy

    def _rect_in_zoom(self, x0, y0, x1, y1):
        return not (x1 < 0 or y1 < 0 or x0 > self.zoom_w or y0 > self.zoom_h)

    def _point_in_zoom(self, x, y):
        return 0 <= x <= self.zoom_w and 0 <= y <= self.zoom_h

    def _log(self, message):
        self.log.configure(state="normal")
        self.log.insert("end", message + "\n\n")
        self.log.see("end")
        self.log.configure(state="disabled")


def main():
    root = tk.Tk()
    StarshipGame(root)
    root.mainloop()


if __name__ == "__main__":
    main()
