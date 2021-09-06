from enum import Enum
from math import sqrt, pow
from PIL import Image

POS_INF = float('inf')

Color = tuple[int, int, int]
Vec2 = tuple[float, float]
Vec3 = tuple[float, float, float]

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
    p_x = int(img.width / 2. + point[0])
    p_y = int(img.height / 2. - point[1]) - 1
    if 0 <= p_x < img.width and 0 <= p_y < img.height:
        pixels[p_x, p_y] = color


###### algebra ######
def dot(a, b):
    return a[0]*b[0] + a[1]*b[1] + a[2]*b[2]


def length(a):
    return sqrt(dot(a, a))


def scalar_multiply(a, s):
    return (a[0]*s, a[1]*s, a[2]*s)


def add(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def subtract(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _clamp_value(s):
    return int(min(255, max(0, s)))


def clamp(a):
    return (_clamp_value(a[0]), _clamp_value(a[1]), _clamp_value(a[2]))


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
    def __init__(self, light_type: LightType, intensity: float, position: Vec3 = None, direction: Vec3 = None):
        self.light_type = light_type
        self.intensity = intensity
        self.position = position
        self.direction = direction


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
    origin_to_sphere = subtract(origin, sphere.center)

    a = dot(direction, direction)
    b = 2*dot(origin_to_sphere, direction)
    c = dot(origin_to_sphere, origin_to_sphere) - sphere.r2

    discriminant = b*b - (4. * a * c)

    # no real solutions, so there's no intersection
    if discriminant < 0:
        return (POS_INF, POS_INF)

    sqrt_disc = sqrt(discriminant)

    t_1 = (-b + sqrt_disc) / (2. * a)
    t_2 = (-b - sqrt_disc) / (2. * a)
    return (t_1, t_2)


def compute_lighting(point: Vec3, normal: Vec3, view: Vec3, spheres: list[Sphere], lights: list[Light], specular: int) -> float:
    intensity = 0.0
    length_n = length(normal)
    length_v = length(view)

    for light in lights:
        if light.light_type == LightType.AMBIENT:
            intensity += light.intensity
            continue


        if light.light_type == LightType.POINT:
            light_direction = subtract(light.position, point)
            t_max = 1.0
        else:
            light_direction = light.direction
            t_max = POS_INF

        # shadow check
        (shadow_sphere, shadow_t) = closest_intersection(point, light_direction, EPSILON, t_max, spheres)
        if shadow_sphere:
            continue

        # diffuse lighting
        n_dot_l = dot(normal, light_direction)
        if n_dot_l > 0:
            intensity += (light.intensity * (n_dot_l / (length_n * length(light_direction))))

        # specular lighting
        if specular is not None:
            reflection = subtract(scalar_multiply(normal, 2 * dot(normal, light_direction)), light_direction)
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

    view: Vec3 = scalar_multiply(direction, -1.0)
    lighting: float = compute_lighting(point, normal, view, scene.spheres, scene.lights, closest_sphere.specular)
    return scalar_multiply(closest_sphere.color, lighting)


def draw_scene(scene: Scene, img: Image, camera_position: Vec3) -> None:
    (c_w, c_h) = img.size
    pixels = img.load()
    for x in range(int(-c_w/2), int(c_w/2)):
        for y in range(int(-c_h/2), int(c_h/2)):
            direction = canvas_to_viewport((x, y), img, scene)
            color = trace_ray(camera_position, direction, 1.0, POS_INF, scene)
            put_pixel(img, pixels, (x, y), clamp(color))


def main() -> None:
    viewport_size = 1
    projection_plane_z = 1
    camera_position = (0., 0., 0.)
    spheres = [
        Sphere((0., -1, 3), 1., RED, 500),
        Sphere((2, 0., 4), 1., BLUE, 500),
        Sphere((-2, 0., 4), 1., GREEN, 10),
        Sphere((0, -5001, 0), 5000., YELLOW, 1000)
    ]

    lights = [
        Light(LightType.AMBIENT, 0.2),
        Light(LightType.POINT, 0.6, position=[2, 1, 0]),
        Light(LightType.DIRECTIONAL, 0.2, direction=[1, 4, 4]),
    ]
    scene = Scene(
        viewport_size,
        projection_plane_z,
        BACKGROUND_COLOR,
        spheres,
        lights
        )
    img = create_image(600, 600)
    draw_scene(scene, img, camera_position)
    img.show()


if __name__=='__main__': main()
