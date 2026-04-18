#!/usr/bin/env python3
"""
Snake Arena - VSCode에서 실행: python snake_game.py
설치: pip install pygame
패키징: pyinstaller --onefile snake_game.py
"""
import pygame, sys, random, math, json, os
from datetime import date

# ── 상수 ──────────────────────────────────────────────────────────────────────
CELL       = 20
GRID_W     = 40
GRID_H     = 30
WIN_W      = GRID_W * CELL          # 800
HUD_H      = 50
WIN_H      = GRID_H * CELL + HUD_H  # 650
FPS        = 60
BASE_SPEED = 5.0    # 레벨1 초당 이동 횟수
LEVEL_TIME = 120.0  # 레벨당 제한시간(초)
INIT_BODY  = 5      # 초기 몸통 조각 수 (머리+5=6)
FOOD_LIFE  = 15.0   # 먹이 유지 시간(초)

# ── 색상 ──────────────────────────────────────────────────────────────────────
C_BG     = (17,  17,  23)
C_HUD    = (10,  10,  15)
C_GRID   = (28,  28,  38)
C_WHITE  = (255, 255, 255)
C_GRAY   = (140, 140, 140)
C_GREEN  = (0,   255, 136)
C_DKGRN  = (0,   170,  85)
C_RED    = (255,  68,  68)
C_YELLOW = (255, 215,   0)
C_DKBTN  = (50,   50,  70)

AI_PALETTE = [
    ((255, 68,  68),  (180, 30,  30)),
    ((68,  136, 255), (30,  80,  180)),
    ((255, 170,   0), (180, 100,   0)),
    ((170,  68, 255), (100,  30,  180)),
    ((0,   204, 255), (0,   130,  180)),
    ((255, 136, 170), (180,  80,  110)),
    ((136, 255,  68), (80,  180,   30)),
    ((255, 102,   0), (180,  60,    0)),
    ((68,  255, 170), (30,  180,  100)),
    ((255,  68, 255), (180,  30,  180)),
]

# ── 방향 ──────────────────────────────────────────────────────────────────────
UP, DOWN, LEFT, RIGHT = (0,-1),(0,1),(-1,0),(1,0)
ALL_DIRS = [UP, DOWN, LEFT, RIGHT]

def tl(d):  return ( d[1], -d[0])   # 왼쪽 회전 (CCW 90°)
def tr(d):  return (-d[1],  d[0])   # 오른쪽 회전 (CW 90°)
def opp(d): return (-d[0], -d[1])   # 반대 방향

# ── 상태 상수 ─────────────────────────────────────────────────────────────────
MENU = "menu"
COUNTDOWN = "cd"
PLAYING = "play"
PAUSED = "pause"
LVL_WIN = "lw"
LVL_FAIL = "lf"
VICTORY = "vic"
NAME_IN = "ni"
HI_SCORES = "hs"

# ── Snake 클래스 ───────────────────────────────────────────────────────────────
class Snake:
    def __init__(self, segs, direction, colors, is_player=False):
        self.segs      = list(segs)      # [(x,y), ...] 인덱스0=머리
        self.dir       = direction
        self.colors    = colors          # (밝은색, 어두운색)
        self.is_player = is_player
        self.alive     = True
        self.grow_q    = 0
        self.turn_q    = []              # 입력 큐 (최대 2)

    @property
    def head(self):       return self.segs[0]
    @property
    def length(self):     return len(self.segs)
    @property
    def body_count(self): return len(self.segs) - 1

    def queue_turn(self, rel):
        """rel='L' or 'R': 현재 방향 기준 상대 회전"""
        base = self.turn_q[-1] if self.turn_q else self.dir
        nd = tl(base) if rel == 'L' else tr(base)
        if nd != opp(base) and len(self.turn_q) < 2:
            self.turn_q.append(nd)

    def apply_turn(self):
        if self.turn_q:
            self.dir = self.turn_q.pop(0)

    def next_head(self):
        return (self.head[0] + self.dir[0], self.head[1] + self.dir[1])

    def move(self, grow=False):
        self.segs.insert(0, self.next_head())
        if not grow:
            self.segs.pop()

    def grow(self, n=1):
        self.grow_q += n


# ── Food 클래스 ───────────────────────────────────────────────────────────────
class Food:
    def __init__(self, x, y, color):
        self.x, self.y = x, y
        self.color = color
        self.age   = 0.0
        self.phase = random.uniform(0, math.pi * 2)

    @property
    def alive(self): return self.age < FOOD_LIFE


# ── 시각 파티클 (폭발 효과) ────────────────────────────────────────────────────
class VParticle:
    def __init__(self, px, py, color):
        a = random.uniform(0, math.pi * 2)
        v = random.uniform(60, 220)
        self.x, self.y = float(px), float(py)
        self.vx, self.vy = math.cos(a) * v, math.sin(a) * v
        self.color = color
        self.alpha = 255
        self.size  = random.uniform(3, 7)
        self.life  = random.uniform(0.4, 1.0)
        self.age   = 0.0

    def update(self, dt):
        self.x  += self.vx * dt
        self.y  += self.vy * dt
        self.vx *= 0.90
        self.vy *= 0.90
        self.age += dt
        self.alpha = max(0, int(255 * (1 - self.age / self.life)))
        return self.alpha > 0


# ── 점수 관리 (JSON 파일) ──────────────────────────────────────────────────────
SCORE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "snake_scores.json")

def _load():
    try:
        with open(SCORE_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {"high_scores": []}

def _save(data):
    try:
        with open(SCORE_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def is_new_record(total):
    hs = _load()["high_scores"]
    return len(hs) < 10 or total > hs[-1]["total"]

def add_score(name, total, per_level):
    data = _load()
    data["high_scores"].append({
        "name": name.strip() or "익명",
        "total": total,
        "levels": per_level,
        "date": date.today().strftime("%Y-%m-%d"),
    })
    data["high_scores"].sort(key=lambda e: -e["total"])
    data["high_scores"] = data["high_scores"][:10]
    _save(data)

def get_scores():
    return _load()["high_scores"]


# ── AI 판단 ───────────────────────────────────────────────────────────────────
def flood_fill(sx, sy, occ, limit=50):
    visited, q, cnt = {(sx, sy)}, [(sx, sy)], 0
    while q and cnt < limit:
        x, y = q.pop(0)
        cnt += 1
        for d in ALL_DIRS:
            nx, ny = x + d[0], y + d[1]
            p = (nx, ny)
            if 0 <= nx < GRID_W and 0 <= ny < GRID_H and p not in occ and p not in visited:
                visited.add(p)
                q.append(p)
    return cnt

def ai_decide(snake, all_snakes, food_list, occ):
    best_dir, best_score = snake.dir, -1e9
    for d in [snake.dir, tl(snake.dir), tr(snake.dir)]:
        nx, ny = snake.head[0] + d[0], snake.head[1] + d[1]
        if not (0 <= nx < GRID_W and 0 <= ny < GRID_H):
            continue
        if (nx, ny) in occ:
            continue
        s = random.uniform(-25, 25)
        ff = flood_fill(nx, ny, occ, 50)
        s += (min(ff, 30) * 2) if ff >= snake.length + 3 else -600
        for f in food_list:
            dist = abs(nx - f.x) + abs(ny - f.y)
            if dist < 12:
                s += 100 / (dist + 1)
        for e in all_snakes:
            if e is snake or not e.alive:
                continue
            if e.length < snake.length:
                d2 = abs(nx - e.head[0]) + abs(ny - e.head[1])
                s += 80 / (d2 + 1)
        if s > best_score:
            best_score, best_dir = s, d
    return best_dir


# ── 렌더링 도우미 ─────────────────────────────────────────────────────────────
def draw_rr(surf, col, x, y, w, h, r):
    """둥근 사각형 그리기"""
    r = min(r, w // 2, h // 2)
    pygame.draw.rect(surf, col, (x + r, y, w - 2*r, h))
    pygame.draw.rect(surf, col, (x, y + r, w, h - 2*r))
    for cx, cy in [(x+r, y+r), (x+w-r, y+r), (x+r, y+h-r), (x+w-r, y+h-r)]:
        pygame.draw.circle(surf, col, (cx, cy), r)

def c2p(gx, gy):
    """그리드 좌표 → 픽셀 좌표"""
    return gx * CELL, gy * CELL + HUD_H


# ── Game 클래스 ───────────────────────────────────────────────────────────────
class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIN_W, WIN_H))
        pygame.display.set_caption("Snake Arena")
        self.clock  = pygame.time.Clock()
        self._init_fonts()
        self.state     = MENU
        self.level     = 1
        self.lscores   = [0] * 11
        self.snakes    = []
        self.player    = None
        self.food      = []
        self.vparts    = []
        self.lvl_timer = LEVEL_TIME
        self.tick_acc  = 0.0
        self.cd_val    = 3
        self.cd_timer  = 0.0
        self.msg       = ""
        self.died      = False   # 죽음으로 인한 실패 여부
        self.name_buf  = ""
        self.new_rec   = False
        self.confetti  = []
        self.btns      = {}     # 버튼 이름 → pygame.Rect

    def _init_fonts(self):
        fn = self._find_korean_font()
        self.fnt = {
            'cd':  pygame.font.SysFont(fn, 110, bold=True),
            'lg':  pygame.font.SysFont(fn,  48, bold=True),
            'md':  pygame.font.SysFont(fn,  32, bold=True),
            'sm':  pygame.font.SysFont(fn,  22, bold=True),
            'xs':  pygame.font.SysFont(fn,  17),
            'hud': pygame.font.SysFont(fn,  20, bold=True),
        }

    @staticmethod
    def _find_korean_font():
        """한글 지원 시스템 폰트 탐색 (Windows/macOS/Linux)"""
        candidates = [
            "malgun gothic",          # Windows 기본 한글 폰트
            "malgunGothic",
            "Apple SD Gothic Neo",    # macOS
            "AppleSDGothicNeo",
            "AppleGothic",            # macOS (구버전)
            "NanumGothic",            # 나눔고딕 (설치된 경우)
            "Nanum Gothic",
            "nanumgothic",
            "gulim",                  # Windows 굴림
            "dotum",                  # Windows 돋움
            "batang",                 # Windows 바탕
            "UnDotum",                # Linux
            "UnBatang",               # Linux
        ]
        available = {f.lower().replace(" ", "") for f in pygame.font.get_fonts()}
        for c in candidates:
            if c.lower().replace(" ", "") in available:
                return c
        return "arial"  # 한글 미지원 fallback

    # ── 유틸 ──────────────────────────────────────────────────────────────────
    def _tick_sec(self):
        return (1.0 / BASE_SPEED) / (1.05 ** (self.level - 1))

    def _ai_n(self, lv=None):
        return 5 + ((lv or self.level) - 1) * 2

    def _total(self):
        return sum(self.lscores[1:11])

    def _alive_ai(self):
        return [s for s in self.snakes if s.alive and not s.is_player]

    # ── 레벨 초기화 ───────────────────────────────────────────────────────────
    def _init_level(self, lv):
        self.level     = lv
        self.lvl_timer = LEVEL_TIME
        self.tick_acc  = 0.0
        self.snakes    = []
        self.food      = []
        self.vparts    = []
        occ = set()
        ns  = 1 + INIT_BODY  # 머리 1 + 몸통 5 = 6

        py = GRID_H // 2
        psegs = [(4 - i, py) for i in range(ns)]
        self.player = Snake(psegs, RIGHT, (C_GREEN, C_DKGRN), True)
        self.snakes.append(self.player)
        for s in psegs:
            occ.add(s)

        n, tries = 0, 0
        while n < self._ai_n(lv) and tries < 2000:
            tries += 1
            d = random.choice(ALL_DIRS)
            x = random.randint(ns, GRID_W - ns - 1)
            y = random.randint(2, GRID_H - 3)
            segs = [(x - d[0]*i, y - d[1]*i) for i in range(ns)]
            if all(0 <= s[0] < GRID_W and 0 <= s[1] < GRID_H and s not in occ for s in segs):
                col = AI_PALETTE[n % len(AI_PALETTE)]
                self.snakes.append(Snake(segs, d, col))
                for s in segs:
                    occ.add(s)
                n += 1

    # ── 게임 틱 (고정 간격 로직) ──────────────────────────────────────────────
    def _tick(self):
        alive = [s for s in self.snakes if s.alive]
        if not alive:
            return

        occ = set(seg for s in alive for seg in s.segs)
        fl  = [f for f in self.food if f.alive]

        for s in alive:
            if s.is_player:
                s.apply_turn()
            else:
                s.dir = ai_decide(s, alive, fl, occ)

        nh    = {s: s.next_head() for s in alive}
        dying = set()

        # 벽 + 자기 몸 충돌
        for s in alive:
            h = nh[s]
            if not (0 <= h[0] < GRID_W and 0 <= h[1] < GRID_H):
                dying.add(s)
                continue
            tail_exc = 1 if s.grow_q == 0 else 0
            if h in s.segs[1: len(s.segs) - tail_exc]:
                dying.add(s)

        # 머리 vs 머리
        hmap = {}
        for s in alive:
            if s not in dying:
                hmap.setdefault(nh[s], []).append(s)
        for grp in hmap.values():
            if len(grp) < 2:
                continue
            mx = max(x.length for x in grp)
            mn = min(x.length for x in grp)
            for s in grp:
                if mx == mn or s.length == mn:
                    dying.add(s)

        # 머리 vs 다른 뱀 몸통 (몸통 주인이 사망)
        bmap = {}
        for s in alive:
            if s not in dying:
                for i, seg in enumerate(s.segs):
                    if i > 0:
                        bmap.setdefault(seg, []).append(s)
        for s in alive:
            if s not in dying:
                for owner in bmap.get(nh[s], []):
                    if owner is not s:
                        dying.add(owner)

        for s in dying:
            s.alive = False
            self._scatter(s)

        for s in alive:
            if not s.alive:
                continue
            g = s.grow_q > 0
            if g:
                s.grow_q -= 1
            s.move(g)

        # 먹이 수집
        for f in self.food:
            if not f.alive:
                continue
            for s in alive:
                if s.alive and s.head == (f.x, f.y):
                    s.grow(1)
                    f.age = FOOD_LIFE
                    break
        self.food = [f for f in self.food if f.age < FOOD_LIFE + 1]

        if self.player and not self.player.alive:
            self.lscores[self.level] = 0
            self.msg  = "사용자 뱀이 사망! 게임 오버"
            self.died = True
            self.state = LVL_FAIL
            return

        if not self._alive_ai():
            self._win()

    def _scatter(self, sn):
        occ = set(seg for s in self.snakes if s.alive for seg in s.segs)
        for seg in sn.segs:
            placed = False
            for cand in [seg] + [(seg[0]+dx, seg[1]+dy) for dx, dy in [(1,0),(-1,0),(0,1),(0,-1)]]:
                if (0 <= cand[0] < GRID_W and 0 <= cand[1] < GRID_H
                        and cand not in occ
                        and not any(f.alive and (f.x, f.y) == cand for f in self.food)):
                    self.food.append(Food(cand[0], cand[1], sn.colors[0]))
                    placed = True
                    break
            px, py = c2p(seg[0], seg[1])
            for _ in range(4):
                self.vparts.append(VParticle(px + CELL//2, py + CELL//2, sn.colors[0]))

    def _timer_end(self):
        if not (self.player and self.player.alive):
            return
        al = [s for s in self.snakes if s.alive]
        mx = max(s.length for s in al) if al else 0
        if self.player.length >= mx:
            self._win()
        else:
            self.lscores[self.level] = self.player.body_count
            self.msg   = "시간 종료! 가장 큰 뱀이 아니었습니다"
            self.died  = False
            self.state = LVL_FAIL

    def _win(self):
        self.lscores[self.level] = self.player.body_count if self.player else 0
        if self.level >= 10:
            self.new_rec = is_new_record(self._total())
            self.state   = VICTORY
            if self.new_rec:
                self._gen_confetti()
        else:
            self.state = LVL_WIN

    def _gen_confetti(self):
        cols = [C_GREEN, C_YELLOW, C_RED, (68,136,255), (255,170,0), (170,68,255)]
        self.confetti = [{
            'x': random.randint(0, WIN_W), 'y': random.randint(-120, -5),
            'vx': random.uniform(-50, 50),  'vy': random.uniform(130, 300),
            'rot': random.uniform(0, 360),  'rv': random.uniform(-250, 250),
            'w': random.randint(8, 18),     'h': random.randint(4, 10),
            'color': random.choice(cols),
        } for _ in range(90)]

    def _upd_confetti(self, dt):
        for c in self.confetti:
            c['x'] += c['vx'] * dt
            c['y'] += c['vy'] * dt
            c['rot'] = (c['rot'] + c['rv'] * dt) % 360
            if c['y'] > WIN_H + 20:
                c['x'] = random.randint(0, WIN_W)
                c['y'] = random.randint(-120, -5)

    # ── 업데이트 ──────────────────────────────────────────────────────────────
    def update(self, dt):
        dt = min(dt, 0.1)

        if self.state == COUNTDOWN:
            self.cd_timer += dt
            if self.cd_timer >= 1.0:
                self.cd_timer -= 1.0
                self.cd_val -= 1
                if self.cd_val < 0:
                    self.state = PLAYING

        elif self.state == PLAYING:
            self.lvl_timer = max(0.0, self.lvl_timer - dt)
            if self.lvl_timer == 0.0:
                self._timer_end()
                return
            for f in self.food:
                f.age += dt
            self.vparts = [p for p in self.vparts if p.update(dt)]
            ts = self._tick_sec()
            self.tick_acc += dt
            while self.tick_acc >= ts and self.state == PLAYING:
                self._tick()
                self.tick_acc -= ts

        elif self.state in (VICTORY, NAME_IN):
            self._upd_confetti(dt)

    # ── 그리기 ────────────────────────────────────────────────────────────────
    def draw(self):
        self.btns.clear()
        self.screen.fill(C_BG)

        if self.state == MENU:
            self._d_menu()
        elif self.state == HI_SCORES:
            self._d_hiscores()
        else:
            self._d_game()
            if self.state == COUNTDOWN:
                self._d_cd()
            elif self.state == PAUSED:
                self._d_ov(); self._d_paused()
            elif self.state == LVL_WIN:
                self._d_ov(); self._d_lvlwin()
            elif self.state == LVL_FAIL:
                self._d_ov(); self._d_lvlfail()
            elif self.state in (VICTORY, NAME_IN):
                self._d_ov()
                self._d_confetti()
                if self.state == VICTORY:
                    self._d_victory()
                else:
                    self._d_namein()

        pygame.display.flip()

    # ── 공통 UI 도우미 ────────────────────────────────────────────────────────
    def _btn(self, key, label, cx, cy, w=240, h=46, bg=None, fg=(0, 0, 0)):
        if bg is None:
            bg = C_GREEN
        r = pygame.Rect(cx - w//2, cy - h//2, w, h)
        pygame.draw.rect(self.screen, bg, r, border_radius=8)
        ts = self.fnt['sm'].render(label, True, fg)
        self.screen.blit(ts, (r.centerx - ts.get_width()//2, r.centery - ts.get_height()//2))
        self.btns[key] = r

    def _ctr(self, surf, y):
        self.screen.blit(surf, ((WIN_W - surf.get_width()) // 2, y))

    def _d_ov(self):
        ov = pygame.Surface((WIN_W, WIN_H), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 185))
        self.screen.blit(ov, (0, 0))

    # ── 게임 화면 ─────────────────────────────────────────────────────────────
    def _d_game(self):
        for x in range(GRID_W + 1):
            pygame.draw.line(self.screen, C_GRID, (x*CELL, HUD_H), (x*CELL, WIN_H))
        for y in range(GRID_H + 1):
            pygame.draw.line(self.screen, C_GRID, (0, y*CELL+HUD_H), (WIN_W, y*CELL+HUD_H))

        t = pygame.time.get_ticks() / 1000
        for f in self.food:
            if not f.alive:
                continue
            fade  = max(0, 1 - f.age / FOOD_LIFE)
            pulse = 0.8 + 0.2 * math.sin(t * 3 + f.phase)
            r  = max(1, int(CELL * 0.35 * pulse))
            cx2, cy2 = f.x*CELL + CELL//2, f.y*CELL + HUD_H + CELL//2
            col = tuple(int(c * fade) for c in f.color)
            pygame.draw.circle(self.screen, col, (cx2, cy2), r)
            if r > 3:
                inner = tuple(min(255, int(c * 1.4)) for c in col)
                pygame.draw.circle(self.screen, inner, (cx2, cy2), r - 3)

        for p in self.vparts:
            sz = max(1, int(p.size))
            s  = pygame.Surface((sz*2, sz*2), pygame.SRCALPHA)
            pygame.draw.circle(s, (*p.color[:3], p.alpha), (sz, sz), sz)
            self.screen.blit(s, (int(p.x - sz), int(p.y - sz)))

        for sn in self.snakes:
            if sn.alive:
                self._d_snake(sn)

        self._d_hud()

    def _d_snake(self, sn):
        n = len(sn.segs)
        for i in range(n - 1, -1, -1):
            seg = sn.segs[i]
            px, py = seg[0]*CELL, seg[1]*CELL + HUD_H
            ins = 2; x, y, sz = px+ins, py+ins, CELL-ins*2
            rad = max(3, sz // 3)
            if i == 0:
                draw_rr(self.screen, sn.colors[0], x, y, sz, sz, rad)
                d  = sn.dir
                ex, ey = x + sz//2, y + sz//2
                eo = sz // 4
                if d[0] != 0:
                    e1 = (ex + d[0]*2, ey - eo)
                    e2 = (ex + d[0]*2, ey + eo)
                else:
                    e1 = (ex - eo, ey + d[1]*2)
                    e2 = (ex + eo, ey + d[1]*2)
                for e in (e1, e2):
                    pygame.draw.circle(self.screen, C_WHITE, e, 3)
                    pygame.draw.circle(self.screen, (0,0,0), (e[0]+d[0], e[1]+d[1]), 1)
            else:
                a   = 0.55 + 0.45 * (1 - i / n)
                col = tuple(int(c * a) for c in sn.colors[1])
                draw_rr(self.screen, col, x, y, sz, sz, max(2, rad - 1))

    def _d_hud(self):
        pygame.draw.rect(self.screen, C_HUD, (0, 0, WIN_W, HUD_H))
        pygame.draw.line(self.screen, (50, 50, 65), (0, HUD_H-1), (WIN_W, HUD_H-1))
        lv = self.fnt['hud'].render(f"LEVEL {self.level}", True, C_GREEN)
        self.screen.blit(lv, (12, (HUD_H - lv.get_height()) // 2))
        t  = max(0, self.lvl_timer)
        tc = C_RED if t <= 30 else C_WHITE
        ts = self.fnt['hud'].render(f"{int(t)//60}:{int(t)%60:02d}", True, tc)
        self.screen.blit(ts, ((WIN_W - ts.get_width())//2, (HUD_H - ts.get_height())//2))
        pc = self.player.body_count if self.player and self.player.alive else 0
        ai = len(self._alive_ai())
        rs = self.fnt['hud'].render(f"몸통:{pc}  적:{ai}", True, C_GREEN)
        self.screen.blit(rs, (WIN_W - rs.get_width() - 12, (HUD_H - rs.get_height())//2))

    # ── 카운트다운 ────────────────────────────────────────────────────────────
    def _d_cd(self):
        v   = max(0, self.cd_val)
        lbl = str(v) if v > 0 else "GO!"
        col = C_GREEN if v == 0 else C_WHITE
        t   = self.fnt['cd'].render(lbl, True, col)
        self._ctr(t, (WIN_H - t.get_height()) // 2)
        s = self.fnt['sm'].render(f"레벨 {self.level}  —  AI {self._ai_n()}마리", True, C_GRAY)
        self._ctr(s, WIN_H // 2 + 80)

    # ── 메뉴 ──────────────────────────────────────────────────────────────────
    def _d_menu(self):
        self._ctr(self.fnt['lg'].render("Snake Arena", True, C_GREEN), 140)
        self._ctr(self.fnt['xs'].render("뱀들을 잡아먹고 가장 큰 뱀이 되어라!", True, C_GRAY), 210)
        self._btn('start',    "게임 시작",   WIN_W//2, 300, w=260, h=52)
        self._btn('hiscores', "최고 기록",   WIN_W//2, 368, w=260, h=52, bg=C_DKBTN, fg=C_WHITE)
        ctrl = self.fnt['xs'].render("← 왼쪽 회전   → 오른쪽 회전   Space 일시정지", True, (80,80,110))
        self._ctr(ctrl, 460)

    # ── 일시정지 ──────────────────────────────────────────────────────────────
    def _d_paused(self):
        self._ctr(self.fnt['md'].render("일시정지", True, C_WHITE), 215)
        self._btn('resume', "계속하기", WIN_W//2, 310)
        self._btn('menu',   "메인 메뉴", WIN_W//2, 372, bg=C_DKBTN, fg=C_WHITE)

    # ── 레벨 클리어 ───────────────────────────────────────────────────────────
    def _d_lvlwin(self):
        badge = self.fnt['sm'].render(f"LEVEL {self.level} CLEAR!", True, (0,0,0))
        br = pygame.Rect(WIN_W//2 - badge.get_width()//2 - 16, 165, badge.get_width()+32, 38)
        pygame.draw.rect(self.screen, C_GREEN, br, border_radius=20)
        self.screen.blit(badge, (br.x+16, br.y+8))
        self._ctr(self.fnt['md'].render("레벨 클리어!", True, C_WHITE), 220)
        self._ctr(self.fnt['sm'].render(f"내 뱀 크기: {self.lscores[self.level]} 조각", True, C_GREEN), 278)
        if self.level < 10:
            nxt = self.fnt['xs'].render(f"다음: AI {self._ai_n(self.level+1)}마리, 속도 +5%", True, C_GRAY)
            self._ctr(nxt, 318)
        self._btn('next', "다음 레벨 ->", WIN_W//2, 395)

    # ── 게임 오버 / 레벨 실패 ────────────────────────────────────────────────
    def _d_lvlfail(self):
        self._ctr(self.fnt['md'].render("게임 오버", True, C_RED), 195)
        self._ctr(self.fnt['xs'].render(self.msg, True, C_GRAY), 252)
        total = sum(self.lscores[1:self.level])
        self._ctr(self.fnt['sm'].render(f"현재 총점: {total}", True, C_WHITE), 295)
        if self.died:
            self._btn('newgame', "새 게임 (레벨1)", WIN_W//2, 375)
        else:
            self._btn('retry',   "다시 시도",       WIN_W//2, 375)
        self._btn('menu', "메인 메뉴", WIN_W//2, 435, bg=C_DKBTN, fg=C_WHITE)

    # ── 콘페티 ────────────────────────────────────────────────────────────────
    def _d_confetti(self):
        for c in self.confetti:
            s = pygame.Surface((c['w'], c['h']), pygame.SRCALPHA)
            s.fill((*c['color'], 200))
            rs = pygame.transform.rotate(s, c['rot'])
            self.screen.blit(rs, (int(c['x']), int(c['y'])))

    # ── 승리 화면 ─────────────────────────────────────────────────────────────
    def _d_victory(self):
        total = self._total()
        if self.new_rec:
            self._ctr(self.fnt['lg'].render("Trophy", True, C_YELLOW), 115)
            self._ctr(self.fnt['md'].render("신기록 달성!", True, C_YELLOW), 183)
        self._ctr(self.fnt['md'].render("10레벨 클리어!", True, C_WHITE), 235 if self.new_rec else 200)
        self._ctr(self.fnt['sm'].render(f"최종 점수: {total}", True, C_GREEN), 285 if self.new_rec else 255)
        y0 = 335 if self.new_rec else 310
        self._btn('enter_name', "이름 입력 & 저장", WIN_W//2, y0,      w=280)
        self._btn('hiscores',   "최고 기록",         WIN_W//2, y0+62,   w=280, bg=C_DKBTN, fg=C_WHITE)
        self._btn('menu',       "메인 메뉴",          WIN_W//2, y0+124,  w=280, bg=C_DKBTN, fg=C_WHITE)

    # ── 이름 입력 화면 ────────────────────────────────────────────────────────
    def _d_namein(self):
        total = self._total()
        if self.new_rec:
            self._ctr(self.fnt['lg'].render("Trophy", True, C_YELLOW), 105)
            self._ctr(self.fnt['md'].render("신기록 달성!", True, C_YELLOW), 170)
        self._ctr(self.fnt['sm'].render(f"최종 점수: {total}", True, C_GREEN), 222 if self.new_rec else 195)
        self._ctr(self.fnt['sm'].render("이름을 입력하세요:", True, C_WHITE), 262 if self.new_rec else 240)
        box = pygame.Rect(WIN_W//2 - 150, 293 if self.new_rec else 275, 300, 48)
        pygame.draw.rect(self.screen, (40, 40, 55), box, border_radius=6)
        pygame.draw.rect(self.screen, C_GREEN, box, 2, border_radius=6)
        cur = "|" if (pygame.time.get_ticks() // 500) % 2 == 0 else " "
        ins = self.fnt['sm'].render(self.name_buf + cur, True, C_WHITE)
        self.screen.blit(ins, (box.x + 10, box.y + (box.h - ins.get_height())//2))
        self._btn('save', "저장", WIN_W//2, box.bottom + 46, w=200)

    # ── 최고 기록 ─────────────────────────────────────────────────────────────
    def _d_hiscores(self):
        self._ctr(self.fnt['lg'].render("최고 기록", True, C_GREEN), 50)
        sc     = get_scores()
        medals = ["1위","2위","3위","4위","5위","6위","7위","8위","9위","10위"]
        y = 125
        if not sc:
            self._ctr(self.fnt['sm'].render("아직 기록이 없습니다", True, C_GRAY), 300)
        for i, e in enumerate(sc):
            col = C_YELLOW if i == 0 else (C_WHITE if i < 3 else C_GRAY)
            row = self.fnt['sm'].render(
                f"{medals[i]}  {e['name']:<12} {e['total']:>6}점  {e['date']}",
                True, col)
            self._ctr(row, y)
            y += 44
        self._btn('back', "<- 돌아가기", WIN_W//2, WIN_H - 60, w=200, bg=C_DKBTN, fg=C_WHITE)

    # ── 입력 처리 ─────────────────────────────────────────────────────────────
    def handle(self, ev):
        if ev.type == pygame.QUIT:
            pygame.quit(); sys.exit()

        if ev.type == pygame.KEYDOWN:
            if self.state == PLAYING:
                if ev.key == pygame.K_LEFT:
                    self.player.queue_turn('L')
                elif ev.key == pygame.K_RIGHT:
                    self.player.queue_turn('R')
                elif ev.key in (pygame.K_SPACE, pygame.K_ESCAPE):
                    self.state = PAUSED
            elif self.state == PAUSED:
                if ev.key in (pygame.K_SPACE, pygame.K_ESCAPE):
                    self.state = PLAYING
            elif self.state == NAME_IN:
                if ev.key == pygame.K_RETURN:
                    self._do_save()
                elif ev.key == pygame.K_BACKSPACE:
                    self.name_buf = self.name_buf[:-1]
                elif len(self.name_buf) < 12 and ev.unicode.isprintable():
                    self.name_buf += ev.unicode

        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            p = ev.pos
            def hit(k): return k in self.btns and self.btns[k].collidepoint(p)

            if self.state == MENU:
                if hit('start'):      self._go(1, reset=True)
                elif hit('hiscores'): self.state = HI_SCORES
            elif self.state == PAUSED:
                if hit('resume'):     self.state = PLAYING
                elif hit('menu'):     self.state = MENU
            elif self.state == LVL_WIN:
                if hit('next'):       self._go(self.level + 1)
            elif self.state == LVL_FAIL:
                if hit('retry'):      self._go(self.level, reset=False)
                elif hit('newgame'):  self._go(1, reset=True)
                elif hit('menu'):     self.state = MENU
            elif self.state == VICTORY:
                if hit('enter_name'): self.state = NAME_IN; self.name_buf = ""
                elif hit('hiscores'): self.state = HI_SCORES
                elif hit('menu'):     self.state = MENU
            elif self.state == NAME_IN:
                if hit('save'):       self._do_save()
            elif self.state == HI_SCORES:
                if hit('back'):       self.state = MENU

    def _do_save(self):
        add_score(self.name_buf, self._total(), self.lscores[1:11])
        self.state = HI_SCORES

    def _go(self, lv, reset=False):
        if reset:
            self.lscores = [0] * 11
        self._init_level(lv)
        self.cd_val   = 3
        self.cd_timer = 0.0
        self.state    = COUNTDOWN

    # ── 메인 루프 ─────────────────────────────────────────────────────────────
    def run(self):
        while True:
            dt = self.clock.tick(FPS) / 1000.0
            for ev in pygame.event.get():
                self.handle(ev)
            self.update(dt)
            self.draw()


# ── 진입점 ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    Game().run()
