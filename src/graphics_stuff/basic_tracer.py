from enum import Enum
import math
from PIL import Image

POS_INF = float('inf')
NEG_INF = float('-inf')

Color = tuple[int, int, int]
Vec2 = tuple[int, int]
Vec3 = tuple[int, int, int]

BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
WHITE = (255, 255, 255)
BACKGROUND_COLOR = BLACK


def create_image(width: int, height: int, mode='RGB') -> Image:
    return Image.new(mode, (width, height))


def put_pixel(img: Image, point: Vec2, color: Color) -> None:
    (c_w, c_h) = img.size
    (x, y) = point
    translated_point = (int(c_w / 2 + x), int(c_h / 2 - y) - 1)
    if 0 <= translated_point[0] < img.width and 0 <= translated_point[1] < img.height:
        img.putpixel(translated_point, color)


###### algebra ######
def dot(v1, v2):
    assert len(v1) == len(v2)
    prod = 0
    for i in range(len(v1)):
        prod += (v1[i] * v2[i])
    return prod


def length(v):
    return math.sqrt(dot(v, v))


def scalar_multiply(v, s):
    return tuple(map(lambda x: s*x, v))


def add(v1, v2):
    assert len(v1) == len(v2)
    result = []
    for i in range(len(v1)):
        result.append(v1[i] + v2[i])
    return tuple(result)


def subtract(v1, v2):
    assert len(v1) == len(v2)
    result = []
    for i in range(len(v1)):
        result.append(v1[i] - v2[i])
    return tuple(result)


def clamp(v):
    return tuple(map(lambda x: int(min(255, max(0, x))), v))


#########################


class Sphere:
    def __init__(self, center: Vec3, radius: int, color: Color):
        self.center = center
        self.radius = radius
        self.color = color
        self.r2 = radius*radius


class LightType(Enum):
    AMBIENT = 0
    POINT = 1
    DIRECTIONAL = 2


class Light:
    def __init__(self, light_type: LightType, intensity: int, position: Vec3 = None):
        self.light_type = light_type
        self.intensity = intensity
        self.position = position


class Scene:
    def __init__(self, viewport_size: int, projection_plane: int, camera_position: Vec3, background_color: Color, spheres: list[Sphere], lights: list[Light]):
        self.viewport_size = viewport_size
        self.projection_plane = projection_plane
        self.camera_position = camera_position
        self.background_color = background_color
        self.spheres = spheres
        self.lights = lights


def canvas_to_viewport(canvas_point: Vec2, img: Image, scene: Scene) -> Vec3:
    return (canvas_point[0] * scene.viewport_size / img.width, canvas_point[1] * scene.viewport_size / img.height, scene.projection_plane)


def intersect_ray_sphere(origin: Vec3, direction_vector: Vec3, sphere: Sphere) -> tuple[int, int]:
    CO = subtract(origin, sphere.center)

    a = dot(direction_vector, direction_vector)
    b = 2*dot(CO, direction_vector)
    c = dot(CO, CO) - sphere.r2

    discriminant = b*b - 4*a*c

    if discriminant < 0:
        return (POS_INF, POS_INF)

    sqrt_disc = math.sqrt(discriminant)

    t_1 = (-b + sqrt_disc) / 2*a
    t_2 = (-b - sqrt_disc) / 2*a
    return (t_1, t_2)


def compute_lighting(point: Vec3, normal: Vec3, scene: Scene):
    intensity = 0
    length_n = length(normal)

    for light in scene.lights:
        if light.light_type == LightType.AMBIENT:
            intensity += light.intensity
        else:
            l_vec = None
            if light.light_type == LightType.POINT:
                l_vec = subtract(light.position, point)
            else:
                l_vec = light.position
            n_dot_l = dot(normal, l_vec)
            if n_dot_l > 0:
                intensity += light.intensity * n_dot_l / (length_n * length(l_vec))

    return intensity


def trace_ray(direction: Vec3, t_min: float, t_max: float, scene: Scene) -> Color:
    closest_t = POS_INF
    closest_sphere = None

    for sphere in scene.spheres:
        (t_1, t_2) = intersect_ray_sphere(scene.camera_position, direction, sphere)
        if t_min <= t_1 <= t_max and t_1 < closest_t:
            closest_t = t_1
            closest_sphere = sphere

        if t_min <= t_2 <= t_max and t_2 < closest_t:
            closest_t = t_2
            closest_sphere = sphere

    if closest_sphere is None:
        return BACKGROUND_COLOR

    point = add(scene.camera_position, scalar_multiply(direction, closest_t));
    normal = subtract(point, closest_sphere.center);
    normal = scalar_multiply(normal, 1.0 / length(normal));

    return scalar_multiply(closest_sphere.color, compute_lighting(point, normal, scene));


def draw_scene(scene: Scene, canvas: Image) -> None:
    (c_w, c_h) = canvas.size
    for x in range(int(-c_w/2), int(c_w/2)):
        for y in range(int(-c_h/2), int(c_h/2)):
            direction = canvas_to_viewport((x, y), canvas, scene)
            color = trace_ray(direction, 1, POS_INF, scene)
            put_pixel(canvas, (x, y), clamp(color))


def main() -> None:
    viewport_size = 1
    projection_plane = 1
    camera_position = (0, 0, 0)
    spheres = [
        Sphere((0, -1, 3), 1, RED),
        Sphere((2, 0, 4), 1, BLUE),
        Sphere((-2, 0, 4), 1, GREEN)
    ]

    lights = [
        Light(LightType.AMBIENT, 0.2),
        Light(LightType.POINT, 0.6, [2, 1, 0]),
        Light(LightType.DIRECTIONAL, 0.2, [1, 4, 4]),
    ]
    scene = Scene(
        viewport_size,
        projection_plane,
        camera_position,
        BACKGROUND_COLOR,
        spheres,
        lights
        )
    canvas = create_image(600, 600)
    draw_scene(scene, canvas)
    canvas.show()


if __name__=='__main__': main()
