"""Fit complete furniture scenes to the desktop camera, with one shared floor."""
import itertools
import numpy as np
from grounding import EYE, FORWARD, UP, TAN_HALF_FOV, projected_floor_offset


def corners(lo, hi):
    return np.array(list(itertools.product(*zip(lo, hi))), dtype=float)


def asset_bounds(asset, position, height, yaw):
    from furniture_scene import rotation
    scale = height / max(float(asset.extent[1]), .001)
    anchor = (asset.minimum + asset.maximum) * .5
    anchor[1] = asset.minimum[1]
    return (corners(asset.minimum, asset.maximum) - anchor) @ rotation(yaw).T * scale + position


def scene_bounds(scene):
    """Read placed mesh bounds once; never scan vertex buffers per frame."""
    if hasattr(scene, '_framing_points'):
        return scene._framing_points
    if scene.mode == 'coffee':
        points = [corners(scene.counter_min,scene.counter_max) @ scene.turn.T + scene.stand]
    else:
        points = [corners(scene.chair_min, scene.chair_max) @ scene.turn.T + scene.origin]
        if scene.table:
            lo = scene.table.minimum.copy(); hi = scene.table.maximum.copy()
            lo[1] -= scene.table.minimum[1]; hi[1] -= scene.table.minimum[1]
            points.append(corners(lo, hi) * scene.table_scale + scene.table_position)
        if scene.desk:
            parts = {p['name']: p for p in scene.asset.parts}
            for name, anchor, scale, target in scene.workstation.placements:
                cloud = parts[name]['pos'] @ scene.workstation.source_rotation.T
                bounds = (corners(cloud.min(0), cloud.max(0)) - anchor) * scale + target
                points.append(bounds @ scene.turn.T + scene.origin)
    activity = scene.activity
    if activity:
        f = scene.fit
        if activity.kind == 'tv':
            base = scene.origin + scene.turn @ np.array([f.width*.5, 0, f.upper*2.8])
            for key, position, height, yaw in [('stand', base, .28, scene.facing),
                    ('tv', base + [0, .28, 0], .65, scene.facing+90)]:
                points.append(asset_bounds(activity.assets[key], position, height, yaw))
        if activity.kind in ('coffee', 'window'):
            top = scene.counter_height
            if 'machine' in activity.assets:
                points.append(asset_bounds(activity.assets['machine'], scene.stand+scene.turn@scene.machine_local, .38, scene.machine_yaw))
            bottom = max(top+.15, float(scene.model.rest_canonical['head'][1])-.65)
            points.append(asset_bounds(activity.assets['window'], scene.stand+scene.turn@(scene.window_local+[0,bottom,0]), 1.25, getattr(scene,'window_yaw',scene.facing)))
    # Reserve the whole walking route, including hair and shoes, so the camera
    # doesn't pump while the actor turns, sits or gestures.
    r = scene.model.rest_canonical
    radius = max(.38, abs(r['leftUpperArm'][0]-r['rightUpperArm'][0])*.85)
    height = max(p[1] for p in r.values()) + .25
    envelope = corners([-radius, 0, -radius], [radius, height, radius])
    for position in [np.zeros(3), scene.origin, scene.stand, *scene.route]:
        points.append(envelope+position)
    if scene.table and activity and activity.kind in ('reading','tv'):
        lo=scene.table.minimum.copy();hi=scene.table.maximum.copy()
        lo[1]=hi[1]=0.
        table=corners(lo,hi)*scene.table_scale+scene.table_position
        # Reserve the actor beside the table before the scene starts, so
        # standing to return an object cannot cut off hair or change zoom.
        margin=radius+.25
        low=table.min(0)-[margin,0,margin];high=table.max(0)+[margin,height,margin]
        points.append(corners(low,high))
    scene._framing_points = np.concatenate(points)
    return scene._framing_points


def fit_frame(points, floor, aspect):
    """Uniform scale and pan; no stretching or changes to furniture ergonomics."""
    center = float((points[:,0].min()+points[:,0].max())*.5)
    centered = points - [center, 0, 0]
    grounded = floor - [center, 0, 0]
    def fits(scale):
        offset = projected_floor_offset(grounded*scale)
        camera = centered*scale + UP*offset - EYE
        depth = camera@FORWARD
        return bool(np.all(depth>.1) and
                    np.all(np.abs(camera[:,0]) <= depth*TAN_HALF_FOV*max(.2,aspect)*.92) and
                    np.all(camera@UP <= depth*TAN_HALF_FOV*.92))
    lo, hi = .01, 1.
    for _ in range(18):
        mid = (lo+hi)*.5
        if fits(mid):lo=mid
        else:hi=mid
    return lo, center
