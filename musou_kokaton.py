import math
import os
import random
import sys
import time
import pygame as pg

WIDTH = 1100  # Game window width
HEIGHT = 650  # Game window height
os.chdir(os.path.dirname(os.path.abspath(__file__)))

def check_bound(obj_rct: pg.Rect) -> tuple[bool, bool]:
    """
    Check whether an object is within the screen boundaries.
    Returns a tuple of booleans (horizontal, vertical) indicating
    whether the object is inside the boundaries.
    """
    yoko, tate = True, True
    if obj_rct.left < 0 or WIDTH < obj_rct.right:
        yoko = False
    if obj_rct.top < 0 or HEIGHT < obj_rct.bottom:
        tate = False
    return yoko, tate

def calc_orientation(org: pg.Rect, dst: pg.Rect) -> tuple[float, float]:
    """
    Calculate the direction vector from org to dst.
    Returns a tuple (vx, vy) of the normalized direction vector components.
    """
    x_diff, y_diff = dst.centerx - org.centerx, dst.centery - org.centery
    norm = math.hypot(x_diff, y_diff)
    return x_diff / norm, y_diff / norm

class Bird(pg.sprite.Sprite):
    """
    Bird (player character) class.
    """
    
    delta = {  # 押下キーと移動量の辞書
        pg.K_UP: (0, -1),
        pg.K_DOWN: (0, +1),
        pg.K_LEFT: (-1, 0),
        pg.K_RIGHT: (+1, 0),
    }

    def __init__(self, num: int, xy: tuple[int, int]):
        """
        Initialize the bird sprite.
        """
        super().__init__()
        img0 = pg.transform.rotozoom(pg.image.load(f"fig/{num}.png"), 0, 2.0)
        img = pg.transform.flip(img0, True, False)  # Default image
        self.imgs = {
            (+1, 0): img,  # Right
            (+1, -1): pg.transform.rotozoom(img, 45, 1.0),  # Right-up
            (0, -1): pg.transform.rotozoom(img, 90, 1.0),  # Up
            (-1, -1): pg.transform.rotozoom(img0, -45, 1.0),  # Left-up
            (-1, 0): img0,  # Left
            (-1, +1): pg.transform.rotozoom(img0, 45, 1.0),  # Left-down
            (0, +1): pg.transform.rotozoom(img, -90, 1.0),  # Down
            (+1, +1): pg.transform.rotozoom(img, -45, 1.0),  # Right-down
        }
        self.dire = (+1, 0)
        self.image = self.imgs[self.dire]
        self.rect = self.image.get_rect()
        self.rect.center = xy
        self.speed = 10
        self.state = "normal"  # 状態変数
        self.hyper_life = 0  # 無敵時間のカウント

    def change_img(self, num: int, screen: pg.Surface):
        """
        Change the bird's image.
        """
        self.image = pg.transform.rotozoom(pg.image.load(f"fig/{num}.png"), 0, 2.0)
        screen.blit(self.image, self.rect)

    def update(self, key_lst: list[bool], screen: pg.Surface, score):
        """
        Update the bird's position based on key presses.
        """
        sum_mv = [0, 0]
        for k, mv in __class__.delta.items():
            if key_lst[k]:
                sum_mv[0] += mv[0]
                sum_mv[1] += mv[1]
        self.rect.move_ip(self.speed * sum_mv[0], self.speed * sum_mv[1])
        if check_bound(self.rect) != (True, True):
            self.rect.move_ip(-self.speed * sum_mv[0], -self.speed * sum_mv[1])
        if not (sum_mv[0] == 0 and sum_mv[1] == 0):
            self.dire = tuple(sum_mv)
            self.image = self.imgs[self.dire]
        screen.blit(self.image, self.rect)

        # 無敵モード発動の判定
        if key_lst[pg.K_RSHIFT] and score.value >= 100 and self.state == "normal":
            self.state = "hyper"
            self.hyper_life = 500
            score.value -= 100  # スコアを100消費する------------------------------------------------

        # 無敵モードの処理
        if self.state == "hyper":
            self.image = pg.transform.laplacian(self.image)  
            self.hyper_life -= 1
            if self.hyper_life <= 0:
                self.state = "normal"  # 無敵モード解除

class Bomb(pg.sprite.Sprite):
    """
    Bomb class.
    """
    colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0), (255, 0, 255), (0, 255, 255)]

    def __init__(self, emy: "Enemy", bird: Bird):
        """
        爆弾円Surfaceを生成する
        引数1 emy:爆弾を投下する敵機
        引数2 bird：攻撃対象のこうかとん
        """
        super().__init__()
        rad = random.randint(10, 50)
        self.image = pg.Surface((2 * rad, 2 * rad))
        color = random.choice(__class__.colors)
        pg.draw.circle(self.image, color, (rad, rad), rad)
        self.image.set_colorkey((0, 0, 0))
        self.rect = self.image.get_rect()
        self.vx, self.vy = calc_orientation(emy.rect, bird.rect)
        self.rect.centerx = emy.rect.centerx
        self.rect.centery = emy.rect.centery + emy.rect.height // 2
        self.speed = 6
        self.neutralized = False  # Flag indicating if bomb is neutralized

    def update(self):
        """
        Update the bomb's position.
        """
        self.rect.move_ip(self.speed * self.vx, self.speed * self.vy)
        if check_bound(self.rect) != (True, True):
            self.kill()

class Beam(pg.sprite.Sprite):
    """
    Beam class.
    """
    def __init__(self, bird: Bird):
        """
        Initialize the beam sprite.
        """
        super().__init__()
        self.vx, self.vy = bird.dire
        angle = math.degrees(math.atan2(-self.vy, self.vx))
        self.image = pg.transform.rotozoom(pg.image.load(f"fig/beam.png"), angle, 2.0)
        self.vx = math.cos(math.radians(angle))
        self.vy = -math.sin(math.radians(angle))
        self.rect = self.image.get_rect()
        self.rect.centery = bird.rect.centery + bird.rect.height * self.vy
        self.rect.centerx = bird.rect.centerx + bird.rect.width * self.vx
        self.speed = 10
  
    def update(self):
        """
        Update the beam's position.
        """
        self.rect.move_ip(self.speed * self.vx, self.speed * self.vy)
        if check_bound(self.rect) != (True, True):
            self.kill()

class Explosion(pg.sprite.Sprite):
    """
    Explosion class.
    """
    def __init__(self, obj: "Bomb|Enemy", life: int):
        """
        Initialize the explosion effect.
        """
        super().__init__()
        img = pg.image.load(f"fig/explosion.gif")
        self.imgs = [img, pg.transform.flip(img, 1, 1)]
        self.image = self.imgs[0]
        self.rect = self.image.get_rect(center=obj.rect.center)
        self.life = life

    def update(self):
        """
        Update the explosion effect.
        """
        self.life -= 1
        self.image = self.imgs[self.life // 10 % 2]
        if self.life < 0:
            self.kill()

class Enemy(pg.sprite.Sprite):
    """
    Enemy class.
    """
    imgs = [pg.image.load(f"fig/alien{i}.png") for i in range(1, 4)]

    def __init__(self):
        super().__init__()
        self.original_image = random.choice(__class__.imgs)
        self.image = self.original_image.copy()
        self.rect = self.image.get_rect()
        self.rect.center = random.randint(0, WIDTH), 0
        self.vx, self.vy = 0, +6
        self.bound = random.randint(50, HEIGHT // 2)
        self.state = "down"
        self.interval = random.randint(50, 300)
        self.neutralized = False  # Flag indicating if enemy is neutralized

    def update(self):
        """
        Update the enemy's position.
        """
        if self.rect.centery > self.bound:
            self.vy = 0
            self.state = "stop"
        self.rect.move_ip(self.vx, self.vy)

class Score:
    """
    Score class.
    """
    def __init__(self):
        self.font = pg.font.Font(None, 50)
        self.color = (0, 0, 255)
        self.value = 0
        self.image = self.font.render(f"Score: {self.value}", 0, self.color)
        self.rect = self.image.get_rect()
        self.rect.center = 100, HEIGHT - 50

    def update(self, screen: pg.Surface):
        self.image = self.font.render(f"Score: {self.value}", 0, self.color)
        screen.blit(self.image, self.rect)


class EMP(pg.sprite.Sprite):
    """
    Electromagnetic Pulse (EMP) effect class.
    """
    def __init__(self, emys: pg.sprite.Group, bombs: pg.sprite.Group, screen: pg.Surface):
        super().__init__()
        self.image = pg.Surface((WIDTH, HEIGHT))
        self.image.fill((255, 255, 0))  # Yellow color
        self.image.set_alpha(128)  # Set transparency
        self.rect = self.image.get_rect()
        self.life = int(0.05 * 50)  # Display for 0.05 seconds at 50 fps

        # Neutralize enemies
        for emy in emys:
            if not emy.neutralized:
                emy.neutralized = True
                emy.interval = float('inf')
                emy.image = pg.transform.laplacian(emy.image)
        
        # Neutralize bombs
        for bomb in bombs:
            if not bomb.neutralized:
                bomb.neutralized = True
                bomb.speed *= 0.5

    def update(self):
        self.life -= 1
        if self.life <= 0:
            self.kill()  # Remove EMP effect


class EMP(pg.sprite.Sprite):
    """
    Electromagnetic Pulse (EMP) effect class.
    """
    def __init__(self, emys: pg.sprite.Group, bombs: pg.sprite.Group, screen: pg.Surface):
        super().__init__()
        self.image = pg.Surface((WIDTH, HEIGHT))
        self.image.fill((255, 255, 0))  # Yellow color
        self.image.set_alpha(128)  # Set transparency
        self.rect = self.image.get_rect()
        self.life = int(0.05 * 50)  # Display for 0.05 seconds at 50 fps

        # Neutralize enemies
        for emy in emys:
            if not emy.neutralized:
                emy.neutralized = True
                emy.interval = float('inf')
                emy.image = pg.transform.laplacian(emy.image)
        
        # Neutralize bombs
        for bomb in bombs:
            if not bomb.neutralized:
                bomb.neutralized = True
                bomb.speed *= 0.5

    def update(self):
        self.life -= 1
        if self.life <= 0:
            self.kill()  # Remove EMP effect


class Gravity(pg.sprite.Sprite):
    """
    重力場に関するクラス
    """
    def __init__(self, life: int):
        """
        重力場Surfaceを生成する
        引数 life：発動時間
        """
        super().__init__()
        self.image = pg.Surface((WIDTH, HEIGHT))  # 画面全体のSurface
        self.image.fill((0, 0, 0))  # 黒で塗りつぶす
        self.image.set_alpha(128)  # 半透明度
        self.rect = self.image.get_rect()
        self.life = life  # 発動時間   

    def update(self):
        """
        発動時間を減らし、0未満になったら消す
        """
        self.life -= 1
        if self.life < 0:
            self.kill()
def main():
    pg.display.set_caption("真:こうかとん無双")
    screen = pg.display.set_mode((WIDTH, HEIGHT))
    bg_img = pg.image.load(f"fig/pg_bg.jpg")
    score = Score()

    bird = Bird(3, (900, 400))
    bombs = pg.sprite.Group()
    beams = pg.sprite.Group()
    exps = pg.sprite.Group()
    emys = pg.sprite.Group()
    emps = pg.sprite.Group()
    gravities = pg.sprite.Group() 

    tmr = 0
    clock = pg.time.Clock()
    while True:
        key_lst = pg.key.get_pressed()
        for event in pg.event.get():
            if event.type == pg.QUIT:
                return 0
            if event.type == pg.KEYDOWN:
                if event.key == pg.K_SPACE:
                    beams.add(Beam(bird))
                if event.key == pg.K_e:
                    if score.value >= 20:
                        score.value -= 20
                        emps.add(EMP(emys, bombs, screen))
            if event.type == pg.KEYDOWN and event.key == pg.K_RETURN:
                if score.value >= 0:  
                    gravities.add(Gravity(400))  
                    score.value -= 200  

        screen.blit(bg_img, [0, 0])

        if tmr % 200 == 0:  # 200フレームに1回，敵機を出現させる
            emys.add(Enemy())

        for emy in emys:
            if emy.state == "stop" and tmr % emy.interval == 0:
                if not emy.neutralized:
                    bombs.add(Bomb(emy, bird))

        for gravity in gravities:
            for bomb in pg.sprite.spritecollide(gravity, bombs, True):
                exps.add(Explosion(bomb, 50))  # 爆発エフェクト
                score.value += 1
            for emy in pg.sprite.spritecollide(gravity, emys, True):
                exps.add(Explosion(emy, 100))  # 爆発エフェクト
                score.value += 10

        for emy in pg.sprite.groupcollide(emys, beams, True, True).keys():
            exps.add(Explosion(emy, 100))
            score.value += 1000
            bird.change_img(6, screen)
                # 敵機が停止状態に入ったら，intervalに応じて爆弾投下
            bombs.add(Bomb(emy, bird))


        for bomb in pg.sprite.groupcollide(bombs, beams, True, True).keys():
            exps.add(Explosion(bomb, 50))
            score.value += 1

        # 爆弾とこうかとんの衝突判定
        if bird.state == "normal" and pg.sprite.spritecollideany(bird, bombs):
            bird.change_img(8, screen)  # こうかとん悲しみエフェクト
            score.update(screen)
            pg.display.update()
            time.sleep(2)
            return
        gravities.update() 
        gravities.draw(screen) 
        #bird.update(key_lst, screen)

        if bird.state == "hyper":  # 無敵状態で爆弾に当たった場合
            for bomb in pg.sprite.spritecollide(bird, bombs, True):
                exps.add(Explosion(bomb, 50))  # 爆発エフェクト

        bird.update(key_lst, screen, score)
        beams.update()
        beams.draw(screen)
        emys.update()
        emys.draw(screen)
        bombs.update()
        bombs.draw(screen)
        exps.update()
        exps.draw(screen)
        emps.update()
        emps.draw(screen)
        score.update(screen)
        pg.display.update()
        tmr += 1
        clock.tick(50)


if __name__ == "__main__":
    pg.init()
    main()
    pg.quit()
    sys.exit()
