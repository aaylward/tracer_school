from enum import Enum
from math import sqrt, pow
from PIL import Image

POS_INF = float('inf')

Color = tuple[int, int, int]
Vec2 = tuple[int, int]
Vec3 = tuple[int, int, int]

BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)
WHITE = (255, 255, 255)
BACKGROUND_COLOR = WHITE

EPSILON = 0.0001


def create_image(width: int, height: int, mode='RGB') -> Image:
    return Image.new(mode, (width, height))


def put_pixel(img: Image, pixels, point: Vec2, color: Color) -> None:
    (c_w, c_h) = img.size
    (x, y) = point
    p_x = int(c_w / 2 + x)
    p_y = int(c_h / 2 - y) - 1
    if 0 <= p_x < img.width and 0 <= p_y < img.height:
        pixels[p_x, p_y] = color


###### algebra ######
def dot(v1, v2):
    return v1[0]*v2[0] + v1[1]*v2[1] + v1[2]*v2[2]


def length(v):
    return sqrt(dot(v, v))


def scalar_multiply(v, s):
    return [v[0]*s, v[1]*s, v[2]*s]


def add(v1, v2):
    return [v1[0] + v2[0], v1[1] + v2[1], v1[2] + v2[2]]


def subtract(v1, v2):
    return [v1[0] - v2[0], v1[1] - v2[1], v1[2] - v2[2]]


def clamp(v):
    return (int(min(255, max(0, v[0]))), int(min(255, max(0, v[1]))), int(min(255, max(0, v[2]))))


#########################


class Sphere:
    def __init__(self, center: Vec3, radius: int, color: Color, specular: int):
        self.center = center
        self.radius = radius
        self.color = color
        self.r2 = radius*radius
        self.specular = specular


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
    def __init__(self, viewport_size: int, projection_plane: int, background_color: Color, spheres: list[Sphere], lights: list[Light]):
        self.viewport_size = viewport_size
        self.projection_plane = projection_plane
        self.background_color = background_color
        self.spheres = spheres
        self.lights = lights


def canvas_to_viewport(canvas_point: Vec2, img: Image, scene: Scene) -> Vec3:
    return (canvas_point[0] * scene.viewport_size / img.width, canvas_point[1] * scene.viewport_size / img.height, scene.projection_plane)


def intersect_ray_sphere(origin: Vec3, direction: Vec3, sphere: Sphere) -> tuple[int, int]:
    CO = subtract(origin, sphere.center)

    a = dot(direction, direction)
    b = 2*dot(CO, direction)
    c = dot(CO, CO) - sphere.r2

    discriminant = b*b - 4*a*c

    if discriminant < 0:
        return (POS_INF, POS_INF)

    sqrt_disc = sqrt(discriminant)

    t_1 = (-b + sqrt_disc) / 2*a
    t_2 = (-b - sqrt_disc) / 2*a
    return (t_1, t_2)


def compute_lighting(point: Vec3, normal: Vec3, view: Vec3, spheres: list[Sphere], lights: list[Light], specular: int) -> float:
    intensity = 0
    length_n = length(normal)
    length_v = length(view)

    for light in lights:
        if light.light_type == LightType.AMBIENT:
            intensity += light.intensity
            continue

        if light.light_type == LightType.POINT:
            l_vec = subtract(light.position, point)
            t_max = 1.0
        else:
            l_vec = light.position
            t_max = POS_INF

        # shadow check
        # (shadow_sphere, shadow_t) = closest_intersection(point, l_vec, EPSILON, t_max, spheres)
        # if shadow_sphere is not None:
        #     continue
        #     # pass

        # diffuse lighting
        n_dot_l = dot(normal, l_vec)
        if n_dot_l > 0:
            intensity += (light.intensity * n_dot_l / (length_n * length(l_vec)))

        # specular lighting
        if specular is not None:
            reflection = subtract(scalar_multiply(normal, 2 * dot(normal, l_vec)), l_vec)
            r_dot_v = dot(reflection, view)
            if r_dot_v > 0:
                intensity += (light.intensity * pow(r_dot_v / (length(reflection) * length_v), specular))

    return intensity


def closest_intersection(origin: Vec3, direction: Vec3, t_min: float, t_max: float, spheres: list[Sphere]):
    closest_t = POS_INF
    closest_sphere = None

    for sphere in spheres:
        (t_1, t_2) = intersect_ray_sphere(origin, direction, sphere)
        if t_1 < closest_t and t_min < t_1 < t_max:
            closest_t = t_1
            closest_sphere = sphere

        if t_2 < closest_t and t_min < t_2 < t_max:
            closest_t = t_2
            closest_sphere = sphere

    return (closest_sphere, closest_t)


def trace_ray(origin: Vec3, direction: Vec3, t_min: float, t_max: float, scene: Scene) -> Color:
    (closest_sphere, closest_t) = closest_intersection(origin, direction, t_min, t_max, scene.spheres)

    if closest_sphere is None:
        return BACKGROUND_COLOR

    point: Vec3 = add(origin, scalar_multiply(direction, closest_t));
    normal: Vec3 = subtract(point, closest_sphere.center);
    normal = scalar_multiply(normal, 1.0 / length(normal));

    view: Vec3 = scalar_multiply(direction, -1)
    lighting: float = compute_lighting(point, normal, view, scene.spheres, scene.lights, closest_sphere.specular)
    return scalar_multiply(closest_sphere.color, lighting)


def draw_scene(scene: Scene, canvas: Image, camera_position: Vec3) -> None:
    (c_w, c_h) = canvas.size
    pixels = canvas.load()
    for x in range(int(-c_w/2), int(c_w/2)):
        for y in range(int(-c_h/2), int(c_h/2)):
            direction = canvas_to_viewport((x, y), canvas, scene)
            color = trace_ray(camera_position, direction, 1, POS_INF, scene)
            put_pixel(canvas, pixels, (x, y), clamp(color))


def main() -> None:
    viewport_size = 1
    projection_plane_z = 1
    camera_position = (0, 0, 0)
    spheres = [
        Sphere((0, -1, 3), 1, RED, 500),
        Sphere((2, 0, 4), 1, BLUE, 500),
        Sphere((-2, 0, 4), 1, GREEN, 10),
        Sphere((0, -5001, 0), 5000, YELLOW, 1000)
    ]

    lights = [
        Light(LightType.AMBIENT, 0.2),
        Light(LightType.POINT, 0.6, [2, 1, 0]),
        Light(LightType.DIRECTIONAL, 0.2, [1, 4, 4]),
    ]
    scene = Scene(
        viewport_size,
        projection_plane_z,
        BACKGROUND_COLOR,
        spheres,
        lights
        )
    canvas = create_image(600, 600)
    draw_scene(scene, canvas, camera_position)
    canvas.show()


if __name__=='__main__': main()
