"""Compatibility OpenGL shader; weighted skeletal transforms run on the GPU."""
from OpenGL.GL import *
from OpenGL.GL.shaders import compileProgram,compileShader

def build(bone_count):
    vertex="""#version 120
    uniform mat4 modelBones[BONE_COUNT];
    uniform mat3 modelFlip;
    uniform vec3 modelOrigin;
    uniform float modelScale;
    attribute vec4 jointId;
    attribute vec4 jointWeight;
    attribute vec4 contactRoot;
    attribute float garmentWeight;
    attribute vec4 garmentRest;
    uniform mat4 garmentFrame;
    uniform float garmentHanging;
    uniform vec4 bodyCapsuleStart[6];
    uniform vec4 bodyCapsuleEnd[6];
    uniform vec3 garmentCenter;
    uniform int furnitureEnabled;
    uniform int deskEnabled;
    uniform float seatHeight;
    uniform float deskHeight;
    uniform vec3 deskShift;
    uniform mat4 contactFrame;
    uniform mat4 contactInverse;
    uniform sampler2D seatTop;
    uniform sampler2D chairFront;
    uniform sampler2D deskTop;
    uniform sampler2D deskBack;
    uniform sampler2D deskLeft;
    uniform sampler2D deskRight;
    uniform vec4 seatTopBounds;
    uniform vec4 chairFrontBounds;
    uniform vec4 deskTopBounds;
    uniform vec4 deskBackBounds;
    uniform vec4 deskLeftBounds;
    uniform vec4 deskRightBounds;
    varying vec2 uv;
    varying vec3 surfaceNormal;
    varying vec3 viewPosition;
    vec2 surface(sampler2D field,vec4 bounds,vec2 point) {
        vec2 uv=(point-bounds.xy)/bounds.zw;
        if(any(lessThan(uv,vec2(0.0)))||any(greaterThanEqual(uv,vec2(1.0))))return vec2(0.0);
        return texture2D(field,uv).rg;
    }
    void main() {
        vec4 p=(modelBones[int(jointId.x)]*gl_Vertex)*jointWeight.x;
        p+=(modelBones[int(jointId.y)]*gl_Vertex)*jointWeight.y;
        p+=(modelBones[int(jointId.z)]*gl_Vertex)*jointWeight.z;
        p+=(modelBones[int(jointId.w)]*gl_Vertex)*jointWeight.w;
        vec3 normalized=(modelFlip*p.xyz-modelOrigin)*modelScale;
        vec3 hanging=(modelFlip*(garmentFrame*vec4(garmentRest.xyz,1.0)).xyz-modelOrigin)*modelScale;
        normalized=mix(normalized,hanging,garmentRest.w*garmentHanging);
        mat3 skinNormal=mat3(modelBones[int(jointId.x)])*jointWeight.x+mat3(modelBones[int(jointId.y)])*jointWeight.y+mat3(modelBones[int(jointId.z)])*jointWeight.z+mat3(modelBones[int(jointId.w)])*jointWeight.w;
        vec3 outward=normalize(modelFlip*skinNormal*gl_Normal);
        vec3 radialOutward=normalized-garmentCenter;radialOutward.y=0.0;
        if(length(radialOutward)>0.0000001)outward=normalize(radialOutward);
        if(garmentWeight>0.0){
            vec3 contactStart=normalized;
            for(int pass=0;pass<2;pass++)for(int i=0;i<6;i++){
                vec3 a=bodyCapsuleStart[i].xyz,b=bodyCapsuleEnd[i].xyz;
                float radius=bodyCapsuleStart[i].w;
                vec3 axis=b-a;float t=clamp(dot(normalized-a,axis)/max(dot(axis,axis),0.0000001),0.0,1.0);
                vec3 radial=normalized-mix(a,b,t);float distance=length(radial);
                if(radius>0.0&&distance<radius){
                    float along=dot(radial,outward);
                    float travel=-along+sqrt(max(0.0,along*along+radius*radius-distance*distance));
                    normalized+=outward*travel*garmentWeight;
                }
            }
            vec3 displacement=normalized-contactStart;
            normalized=contactStart+displacement*min(1.0,.12/max(length(displacement),.000000001));
        }
        if(furnitureEnabled==1){
            vec3 rootRaw=(modelBones[int(contactRoot.w)]*vec4(contactRoot.xyz,1.0)).xyz;
            vec3 root=(contactFrame*vec4((modelFlip*rootRaw-modelOrigin)*modelScale,1.0)).xyz;
            vec3 q=(contactFrame*vec4(normalized,1.0)).xyz;
            vec2 hit=surface(seatTop,seatTopBounds,q.xz);
            if(hit.y>.5&&root.y>seatHeight-.14&&q.y<hit.x+.012&&q.y<seatHeight+.12)q.y=hit.x+.012;
            hit=surface(chairFront,chairFrontBounds,q.xy);
            if(hit.y>.5&&q.y>seatHeight+.08&&root.z>hit.x-.04&&q.z<hit.x+.012)q.z=hit.x+.012;
            if(deskEnabled==1){
                q-=deskShift;root-=deskShift;
                hit=surface(deskTop,deskTopBounds,q.xz);
                if(hit.y>.5&&root.y>deskHeight-.08&&q.y<hit.x+.012)q.y=hit.x+.012;
                hit=surface(deskBack,deskBackBounds,q.xy);
                if(hit.y>.5&&root.z<hit.x+.04&&q.z>hit.x-.012)q.z=hit.x-.012;
                hit=surface(deskLeft,deskLeftBounds,q.zy);
                if(hit.y>.5&&root.x<hit.x+.04&&q.x>hit.x-.012)q.x=hit.x-.012;
                hit=surface(deskRight,deskRightBounds,q.zy);
                if(hit.y>.5&&root.x>hit.x-.04&&q.x<hit.x+.012)q.x=hit.x+.012;
                q+=deskShift;
            }
            normalized=(contactInverse*vec4(q,1.0)).xyz;
        }
        gl_Position=gl_ModelViewProjectionMatrix*vec4(normalized,1.0);
        surfaceNormal=normalize(gl_NormalMatrix*modelFlip*skinNormal*gl_Normal);
        viewPosition=(gl_ModelViewMatrix*vec4(normalized,1.0)).xyz;
        uv=gl_MultiTexCoord0.xy;
        gl_FrontColor=gl_Color;
    }""".replace('BONE_COUNT',str(bone_count))
    fragment="""#version 120
    uniform sampler2D modelTexture;
    uniform int textured;
    uniform int toon;
    uniform vec3 shadeColor;
    uniform float shadeShift;
    uniform float shadeToony;
    uniform sampler2D normalTexture;
    uniform int normalMapped;
    uniform float normalStrength;
    uniform sampler2D emissionTexture;
    uniform int emissiveMapped;
    uniform vec3 emissionColor;
    varying vec2 uv;
    varying vec3 surfaceNormal;
    varying vec3 viewPosition;
    void main() {
        vec4 value=gl_Color;
        if(textured==1)value*=texture2D(modelTexture,uv);
        vec3 n=normalize(surfaceNormal);
        if(!gl_FrontFacing)n=-n;
        if(normalMapped==1){
            vec3 dx=dFdx(viewPosition),dy=dFdy(viewPosition);
            vec2 tx=dFdx(uv),ty=dFdy(uv);
            vec3 a=cross(dy,n),b=cross(n,dx);
            vec3 tangent=a*tx.x+b*ty.x,bitangent=a*tx.y+b*ty.y;
            float factor=inversesqrt(max(max(dot(tangent,tangent),dot(bitangent,bitangent)),.000001));
            vec3 map=texture2D(normalTexture,uv).xyz*2.0-1.0;
            map.xy*=normalStrength;
            n=normalize(mat3(tangent*factor,bitangent*factor,n)*map);
        }
        if(toon==1){
            float lighting=dot(n,normalize(vec3(-.35,.55,.85)));
            float width=max(.025,1.0-clamp(shadeToony,0.0,1.0));
            float lit=smoothstep(shadeShift-width,shadeShift+width,lighting);
            value.rgb*=mix(shadeColor,vec3(1.0),lit);
        }
        if(emissiveMapped==1)value.rgb+=texture2D(emissionTexture,uv).rgb*emissionColor;
        gl_FragColor=value;
    }"""
    return compileProgram(compileShader(vertex,GL_VERTEX_SHADER),compileShader(fragment,GL_FRAGMENT_SHADER))
