"""Small visibility graph for swept character footprints around scene props."""
import heapq
import numpy as np


def intersects(a, b, lo, hi):
    """Closed segment against an AABB, including endpoints and grazing."""
    start, end = 0., 1.
    for axis in range(2):
        delta = b[axis]-a[axis]
        if abs(delta)<1e-10:
            if a[axis]<lo[axis] or a[axis]>hi[axis]:return False
        else:
            near, far = sorted(((lo[axis]-a[axis])/delta,(hi[axis]-a[axis])/delta))
            start=max(start,near);end=min(end,far)
            if start>end:return False
    return True


def route(start, goal, obstacles, radius):
    start=np.asarray(start,float);goal=np.asarray(goal,float)
    boxes=[(np.asarray(lo)-radius,np.asarray(hi)+radius) for lo,hi in obstacles]
    def free(a,b):return not any(intersects(a,b,lo,hi) for lo,hi in boxes)
    for point in (start,goal):
        if not free(point,point):raise ValueError('Karakter başlangıcı veya hedefi bir eşyanın içinde.')
    nodes=[start,goal]
    for lo,hi in boxes:
        for x in (lo[0]-.015,hi[0]+.015):
            for z in (lo[1]-.015,hi[1]+.015):
                point=np.array([x,z])
                if free(point,point):nodes.append(point)
    distance={0:0.};parents={};queue=[(0.,0)]
    while queue:
        cost,index=heapq.heappop(queue)
        if cost>distance[index]:continue
        if index==1:break
        for other,point in enumerate(nodes):
            if other==index or not free(nodes[index],point):continue
            candidate=cost+float(np.linalg.norm(nodes[index]-point))
            if candidate<distance.get(other,float('inf')):
                distance[other]=candidate;parents[other]=index;heapq.heappush(queue,(candidate,other))
    if 1 not in distance:raise ValueError('Eşyalara çarpmayan bir yürüyüş yolu bulunamadı.')
    indices=[1]
    while indices[-1]!=0:indices.append(parents[indices[-1]])
    return [nodes[i].copy() for i in reversed(indices[:-1])]
