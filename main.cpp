#ifdef __APPLE__
  #include <GLUT/glut.h>
#else
  #include <GL/glut.h>
#endif
#include <cmath>
#include <string>

const int   WIN_W   = 1100;
const int   WIN_H   = 700;
const float HORIZON = 320.0f;
const float PI      = 3.14159265f;

float laneOffset  = 0.0f;
float carX        = 0.0f;
bool  nightMode   = false;
float cloudOffset = 0.0f;
int   signalTimer = 0;
int   signalPhase = 0;
void filledCircle(float cx, float cy, float r, int seg = 48)
{
    glBegin(GL_TRIANGLE_FAN);
    glVertex2f(cx, cy);
    for(int i = 0; i <= seg; ++i){
        float a = i * 2.f * PI / seg;
        glVertex2f(cx + r * cosf(a), cy + r * sinf(a));
    }
    glEnd();
}

void ringArc(float cx, float cy, float r, float a0, float a1, float thick, int seg = 36)
{
    glBegin(GL_TRIANGLE_STRIP);
    for(int i = 0; i <= seg; ++i){
        float a = a0 + (a1 - a0) * i / seg;
        glVertex2f(cx + (r - thick) * cosf(a), cy + (r - thick) * sinf(a));
    }
    glEnd();
}

void drawText(float x, float y, const std::string& t, void* font = GLUT_BITMAP_HELVETICA_12)
{
    glRasterPos2f(x, y);
    for(char c : t) glutBitmapCharacter(font, c);
}

float roadL(float y){ return   90.f + 345.f * (y / HORIZON); }
float roadR(float y){ return 1010.f - 345.f * (y / HORIZON); }
float roadC(float y){ return (roadL(y) + roadR(y)) * 0.5f; }

void drawOneCloud(float cx, float cy, float scale)
{
    if(nightMode) glColor3f(0.18f, 0.20f, 0.28f);
    else          glColor3f(0.92f, 0.93f, 0.96f);

    struct Puff { float dx, dy, r; };
    Puff puffs[] = {
        {  0.f,   0.f, 28.f}, { 28.f,  8.f, 22.f}, {-28.f,  6.f, 20.f},
        { 52.f,  -2.f, 17.f}, {-50.f, -2.f, 16.f}, { 14.f, 18.f, 19.f},
        {-14.f,  16.f, 18.f}, { 38.f, 14.f, 14.f}, {-38.f, 12.f, 13.f},
    };
    for(auto& p : puffs)
        filledCircle(cx + p.dx * scale, cy + p.dy * scale, p.r * scale, 20);

    if(!nightMode){
        glColor3f(0.76f, 0.79f, 0.86f);
        filledCircle(cx,             cy - 8.f*scale, 22.f*scale, 20);
        filledCircle(cx + 26.f*scale, cy - 4.f*scale, 14.f*scale, 20);
        filledCircle(cx - 24.f*scale, cy - 4.f*scale, 13.f*scale, 20);
    }
}

void drawSky()
{
    glBegin(GL_QUADS);
    if(nightMode){
        glColor3f(0.01f, 0.01f, 0.08f); glVertex2f(0, WIN_H); glVertex2f(WIN_W, WIN_H);
        glColor3f(0.05f, 0.03f, 0.14f);
    } else {
        glColor3f(0.16f, 0.14f, 0.28f); glVertex2f(0, WIN_H); glVertex2f(WIN_W, WIN_H);
        glColor3f(0.36f, 0.26f, 0.44f);
    }
    glVertex2f(WIN_W, HORIZON); glVertex2f(0, HORIZON);
    glEnd();

    if(nightMode){
        glPointSize(2.2f); glColor3f(1, 1, 1);
        glBegin(GL_POINTS);
        unsigned int s = 55555u;
        for(int i = 0; i < 130; ++i){
            s = s*1664525u+1013904223u; float sx=(s&0xFFFF)/65535.f*WIN_W;
            s = s*1664525u+1013904223u; float sy=HORIZON+(s&0xFFFF)/65535.f*(WIN_H-HORIZON);
            glVertex2f(sx, sy);
        }
        glEnd(); glPointSize(1.f);
    }

    glEnable(GL_SCISSOR_TEST);
    glScissor(0, (int)HORIZON, WIN_W, WIN_H - (int)HORIZON);

    struct CloudDef { float bx, by, sc, speed; };
    CloudDef clouds[] = {
        {120.f, HORIZON+280.f, 1.20f, 1.0f}, {380.f, HORIZON+360.f, 0.85f, 0.6f},
        {640.f, HORIZON+220.f, 1.40f, 0.8f}, {860.f, HORIZON+310.f, 0.70f, 1.2f},
        {200.f, HORIZON+140.f, 0.55f, 1.5f}, {500.f, HORIZON+160.f, 0.65f, 1.1f},
        {750.f, HORIZON+400.f, 1.00f, 0.5f}, { 50.f, HORIZON+430.f, 0.80f, 0.9f},
    };
    for(auto& c : clouds){
        float wrap = WIN_W + 160.f;
        float cx   = fmodf(c.bx + cloudOffset * c.speed, wrap);
        if(cx < -80.f) cx += wrap;
        drawOneCloud(cx, c.by, c.sc);
        drawOneCloud(cx + wrap, c.by, c.sc);
    }
    glDisable(GL_SCISSOR_TEST);
}

void drawHills()
{
    glColor3f(nightMode?0.09f:0.24f, nightMode?0.12f:0.36f, nightMode?0.08f:0.20f);
    glBegin(GL_POLYGON);
      glVertex2f(0,HORIZON); glVertex2f(0,HORIZON+52); glVertex2f(160,HORIZON+98);
      glVertex2f(340,HORIZON+60); glVertex2f(550,HORIZON+108); glVertex2f(760,HORIZON+56);
      glVertex2f(960,HORIZON+92); glVertex2f(1100,HORIZON+46); glVertex2f(1100,HORIZON);
    glEnd();
    glColor3f(nightMode?0.06f:0.18f, nightMode?0.09f:0.30f, nightMode?0.05f:0.14f);
    glBegin(GL_POLYGON);
      glVertex2f(0,HORIZON); glVertex2f(0,HORIZON+30); glVertex2f(120,HORIZON+70);
      glVertex2f(280,HORIZON+42); glVertex2f(450,HORIZON+78); glVertex2f(620,HORIZON+38);
      glVertex2f(820,HORIZON+72); glVertex2f(980,HORIZON+34); glVertex2f(1100,HORIZON+56);
      glVertex2f(1100,HORIZON);
    glEnd();
}

void drawGround()
{
    glColor3f(nightMode?0.10f:0.24f, nightMode?0.10f:0.24f, nightMode?0.11f:0.26f);
    glBegin(GL_QUADS);
      glVertex2f(0,HORIZON); glVertex2f(WIN_W,HORIZON);
      glVertex2f(WIN_W,0);   glVertex2f(0,0);
    glEnd();
}

void drawSidewalks()
{
    glColor3f(nightMode?0.22f:0.54f, nightMode?0.21f:0.52f, nightMode?0.19f:0.48f);
    glBegin(GL_QUADS);
      glVertex2f(0,0); glVertex2f(93,0); glVertex2f(437,HORIZON); glVertex2f(0,HORIZON);
    glEnd();
    glColor3f(0.92f, 0.88f, 0.18f);
    glBegin(GL_QUADS);
      glVertex2f(86,0); glVertex2f(96,0); glVertex2f(438,HORIZON); glVertex2f(428,HORIZON);
    glEnd();
    glColor3f(nightMode?0.17f:0.43f, nightMode?0.16f:0.41f, nightMode?0.14f:0.37f);
    glLineWidth(1.f);
    for(int t=1; t<=8; ++t){
        float y = t*(HORIZON/9.f);
        glBegin(GL_LINES); glVertex2f(0,y); glVertex2f(roadL(y)-2.f,y); glEnd();
    }
    glColor3f(nightMode?0.22f:0.54f, nightMode?0.21f:0.52f, nightMode?0.19f:0.48f);
    glBegin(GL_QUADS);
      glVertex2f(1007,0); glVertex2f(1100,0); glVertex2f(1100,HORIZON); glVertex2f(663,HORIZON);
    glEnd();
    glColor3f(0.92f, 0.88f, 0.18f);
    glBegin(GL_QUADS);
      glVertex2f(1004,0); glVertex2f(1014,0); glVertex2f(667,HORIZON); glVertex2f(657,HORIZON);
    glEnd();
    glColor3f(nightMode?0.17f:0.43f, nightMode?0.16f:0.41f, nightMode?0.14f:0.37f);
    for(int t=1; t<=8; ++t){
        float y = t*(HORIZON/9.f);
        glBegin(GL_LINES); glVertex2f(roadR(y)+2.f,y); glVertex2f(WIN_W,y); glEnd();
    }
}
void drawRoad()
{
    glColor3f(nightMode?0.14f:0.27f, nightMode?0.14f:0.27f, nightMode?0.15f:0.28f);
    glBegin(GL_QUADS);
      glVertex2f(90,0); glVertex2f(1010,0); glVertex2f(665,HORIZON); glVertex2f(435,HORIZON);
    glEnd();
    glColor3f(0.88f, 0.88f, 0.88f);
    glLineWidth(3.f);
    glBegin(GL_LINES);
      glVertex2f(90,0); glVertex2f(435,HORIZON);
      glVertex2f(1010,0); glVertex2f(665,HORIZON);
    glEnd();
    glLineWidth(1.f);
}

void drawLaneMarkings()
{
    glColor3f(1.f, 0.80f, 0.f);
    glLineWidth(3.f);
    const int N=22; const float FRAC=0.48f;
    float seg = HORIZON/N;
    for(int i=0; i<N; ++i){
        float yB = i*seg + fmodf(laneOffset, seg);
        float yT = yB + seg*FRAC;
        if(yB > HORIZON) continue;
        if(yT > HORIZON) yT = HORIZON;
        glBegin(GL_LINES); glVertex2f(roadC(yB),yB); glVertex2f(roadC(yT),yT); glEnd();
    }
    glLineWidth(1.f);
}

void drawOneLamp(float lx, float groundY, float sc, bool flip=false)
{
    float ph=285.f*sc, pw=6.f*sc, ah=38.f*sc, lw=22.f*sc, lh=13.f*sc;
    float dir = flip ? -1.f : 1.f;

    glColor3f(0.40f, 0.40f, 0.42f);
    glBegin(GL_QUADS);
      glVertex2f(lx-pw*0.5f,groundY); glVertex2f(lx+pw*0.5f,groundY);
      glVertex2f(lx+pw*0.5f,groundY+ph); glVertex2f(lx-pw*0.5f,groundY+ph);
    glEnd();
    glLineWidth(pw*0.80f);
    glColor3f(0.40f, 0.40f, 0.42f);
    glBegin(GL_LINE_STRIP);
      glVertex2f(lx, groundY+ph);
      glVertex2f(lx+dir*ah*0.45f, groundY+ph+ah*0.38f);
      glVertex2f(lx+dir*ah, groundY+ph+ah*0.20f);
      glVertex2f(lx+dir*(ah+lw*0.5f), groundY+ph);
    glEnd();
    glLineWidth(1.f);
    glColor3f(0.12f, 0.12f, 0.12f);
    float lbx = flip ? lx-ah-lw : lx+ah;
    glBegin(GL_QUADS);
      glVertex2f(lbx,groundY+ph-lh); glVertex2f(lbx+lw,groundY+ph-lh);
      glVertex2f(lbx+lw,groundY+ph); glVertex2f(lbx,groundY+ph);
    glEnd();
    float bx=lbx+lw*0.5f, by2=groundY+ph-lh*0.5f;
    if(nightMode){
        glEnable(GL_BLEND); glBlendFunc(GL_SRC_ALPHA,GL_ONE_MINUS_SRC_ALPHA);
        glColor4f(1.f,0.92f,0.45f,0.25f); filledCircle(bx,by2,lh*2.6f,18);
        glDisable(GL_BLEND);
    }
    glColor3f(1.f,0.95f,0.50f); filledCircle(bx,by2,lh*0.58f,16);
    glColor3f(0.28f,0.28f,0.28f);
    glBegin(GL_QUADS);
      glVertex2f(lx-pw,groundY); glVertex2f(lx+pw,groundY);
      glVertex2f(lx+pw,groundY+pw*2.f); glVertex2f(lx-pw,groundY+pw*2.f);
    glEnd();
}

void drawLampRows()
{
    const int NL=8;
    for(int i=0; i<NL; ++i){
        float t=(float)i/(NL-1), y=t*HORIZON*0.86f, sc=1.f-t*0.76f;
        drawOneLamp(roadL(y)-22.f*sc-10.f, y, sc, false);
        drawOneLamp(roadR(y)+22.f*sc+10.f, y, sc, true);
    }
}

void drawOnePineTree(float tx, float groundY, float sc)
{
    float trunkW=7.f*sc, trunkH=38.f*sc, treeH=220.f*sc;
    glColor3f(nightMode?0.20f:0.40f, nightMode?0.13f:0.24f, nightMode?0.08f:0.10f);
    glBegin(GL_QUADS);
      glVertex2f(tx-trunkW*0.5f,groundY); glVertex2f(tx+trunkW*0.5f,groundY);
      glVertex2f(tx+trunkW*0.5f,groundY+trunkH); glVertex2f(tx-trunkW*0.5f,groundY+trunkH);
    glEnd();

    float darkG=nightMode?0.08f:0.14f, midG=nightMode?0.13f:0.24f, lightG=nightMode?0.18f:0.34f;
    struct Tier { float yBase, halfW, height, shade; };
    float baseY = groundY+trunkH;
    Tier tiers[4]={
        {baseY+treeH*0.00f, 52.f*sc, 70.f*sc, 0.0f},
        {baseY+treeH*0.28f, 40.f*sc, 62.f*sc, 0.06f},
        {baseY+treeH*0.52f, 28.f*sc, 52.f*sc, 0.12f},
        {baseY+treeH*0.72f, 16.f*sc, 44.f*sc, 0.18f},
    };
    for(int t=0; t<4; ++t){
        float yb=tiers[t].yBase, hw=tiers[t].halfW, ht=tiers[t].height, sh=tiers[t].shade;
        glColor3f(darkG+sh*0.5f, midG+sh, darkG+sh*0.3f);
        glBegin(GL_TRIANGLES); glVertex2f(tx-hw,yb); glVertex2f(tx+hw,yb); glVertex2f(tx,yb+ht); glEnd();
        glColor3f(darkG+sh*0.2f, midG+sh*0.5f, darkG+sh*0.1f);
        glBegin(GL_TRIANGLES); glVertex2f(tx-hw,yb); glVertex2f(tx,yb); glVertex2f(tx,yb+ht); glEnd();
        glColor3f(darkG+sh*0.7f, lightG+sh, darkG+sh*0.4f);
        glBegin(GL_TRIANGLES); glVertex2f(tx,yb); glVertex2f(tx+hw,yb); glVertex2f(tx,yb+ht); glEnd();
        if(!nightMode && t==3){
            glColor3f(0.92f,0.96f,0.98f);
            glBegin(GL_TRIANGLES);
              glVertex2f(tx-5.f*sc,yb+ht*0.72f); glVertex2f(tx+5.f*sc,yb+ht*0.72f); glVertex2f(tx,yb+ht);
            glEnd();
        }
    }
}

void drawTreeRows()
{
    const int NT=9;
    for(int i=0; i<NT; ++i){
        float t=(float)i/(NT-1), y=t*HORIZON*0.88f, sc=1.f-t*0.70f;
        drawOnePineTree(roadL(y)-18.f*sc-8.f, y, sc);
        drawOnePineTree(roadR(y)+18.f*sc+8.f, y, sc);
    }
}

// ============================================================
//  CITY BUILDINGS
// ============================================================
void drawBuildingSimple(float bx, float by, float bw, float bh, float r, float g, float b)
{
    glColor3f(r,g,b);
    glBegin(GL_QUADS);
      glVertex2f(bx,by); glVertex2f(bx+bw,by); glVertex2f(bx+bw,by+bh); glVertex2f(bx,by+bh);
    glEnd();
    glColor3f(r*0.70f,g*0.70f,b*0.70f);
    glBegin(GL_QUADS);
      glVertex2f(bx,by+bh); glVertex2f(bx+bw,by+bh);
      glVertex2f(bx+bw+bw*0.10f,by+bh-bh*0.06f); glVertex2f(bx+bw*0.10f,by+bh-bh*0.06f);
    glEnd();
    int cols=(int)(bw/20.f); if(cols<1) cols=1;
    int rows=(int)(bh/22.f); if(rows<1) rows=1;
    float wx=bw/(cols+1), wy=bh/(rows+1);
    for(int row=0; row<rows; ++row)
        for(int col=0; col<cols; ++col){
            float wbx=bx+wx*(col+0.5f)-4.f, wby=by+wy*(row+0.5f)-3.f;
            bool lit = nightMode && ((row*5+col*3)%3!=0);
            glColor3f(lit?0.98f:0.24f, lit?0.90f:0.34f, lit?0.50f:0.66f);
            glBegin(GL_QUADS);
              glVertex2f(wbx,wby); glVertex2f(wbx+8,wby);
              glVertex2f(wbx+8,wby+7); glVertex2f(wbx,wby+7);
            glEnd();
        }
    glColor3f(0.04f,0.04f,0.06f);
    glLineWidth(1.f);
    glBegin(GL_LINE_LOOP);
      glVertex2f(bx,by); glVertex2f(bx+bw,by); glVertex2f(bx+bw,by+bh); glVertex2f(bx,by+bh);
    glEnd();
}

void drawRoadSideBuildings()
{
    const int NB=7;
    float lbW[]={82,70,58,46,36,26,18}, lbH[]={290,250,210,170,135,100,70};
    float lbR[]={0.18f,0.22f,0.26f,0.20f,0.24f,0.18f,0.22f};
    float lbG[]={0.22f,0.18f,0.28f,0.24f,0.20f,0.26f,0.18f};
    float lbB[]={0.30f,0.24f,0.22f,0.32f,0.26f,0.20f,0.28f};
    for(int i=0; i<NB; ++i){
        float t=(float)i/(NB-1), y=t*HORIZON*0.88f, sc=1.f-t*0.72f;
        float bw=lbW[i]*sc, bh=lbH[i]*sc, bx=roadL(y)-bw-36.f*sc;
        drawBuildingSimple(bx,y,bw,bh,nightMode?lbR[i]*0.55f:lbR[i],nightMode?lbG[i]*0.55f:lbG[i],nightMode?lbB[i]*0.55f:lbB[i]);
    }
    float rbW[]={80,68,56,44,34,24,16}, rbH[]={310,260,220,175,140,105,72};
    float rbR[]={0.20f,0.18f,0.24f,0.22f,0.26f,0.20f,0.18f};
    float rbG[]={0.24f,0.20f,0.18f,0.26f,0.22f,0.18f,0.24f};
    float rbB[]={0.32f,0.26f,0.28f,0.22f,0.28f,0.30f,0.20f};
    for(int i=0; i<NB; ++i){
        float t=(float)i/(NB-1), y=t*HORIZON*0.88f, sc=1.f-t*0.72f;
        float bw=rbW[i]*sc, bh=rbH[i]*sc, bx=roadR(y)+36.f*sc;
        drawBuildingSimple(bx,y,bw,bh,nightMode?rbR[i]*0.55f:rbR[i],nightMode?rbG[i]*0.55f:rbG[i],nightMode?rbB[i]*0.55f:rbB[i]);
    }
}

void drawCityBuildings()
{
    struct BData { float x,y,w,h,dep,r,g,b; };
    BData blds[]={
        {  0,252, 72,378,18,0.18f,0.23f,0.30f}, { 60,280, 88,328,20,0.22f,0.18f,0.16f},
        {  0,166, 58,218,14,0.28f,0.24f,0.18f}, { 30,372, 20,250, 8,0.20f,0.20f,0.26f},
        {924,260, 82,368,20,0.18f,0.24f,0.32f}, {986,284, 80,308,18,0.24f,0.18f,0.20f},
        {920,164, 58,208,14,0.26f,0.22f,0.18f},{1058,360, 20,240, 8,0.20f,0.20f,0.26f},
    };
    for(auto& b : blds){
        float dr=nightMode?b.r*0.55f:b.r, dg=nightMode?b.g*0.55f:b.g, db=nightMode?b.b*0.55f:b.b;
        glColor3f(dr,dg,db);
        glBegin(GL_QUADS);
          glVertex2f(b.x,b.y); glVertex2f(b.x+b.w,b.y); glVertex2f(b.x+b.w,b.y+b.h); glVertex2f(b.x,b.y+b.h);
        glEnd();
        glColor3f(dr*0.50f,dg*0.50f,db*0.50f);
        glBegin(GL_QUADS);
          glVertex2f(b.x+b.w,b.y); glVertex2f(b.x+b.w+b.dep,b.y-b.dep*0.40f);
          glVertex2f(b.x+b.w+b.dep,b.y+b.h-b.dep*0.40f); glVertex2f(b.x+b.w,b.y+b.h);
        glEnd();
        glColor3f(dr*0.68f,dg*0.68f,db*0.68f);
        glBegin(GL_QUADS);
          glVertex2f(b.x,b.y+b.h); glVertex2f(b.x+b.w,b.y+b.h);
          glVertex2f(b.x+b.w+b.dep,b.y+b.h-b.dep*0.40f); glVertex2f(b.x+b.dep,b.y+b.h-b.dep*0.40f);
        glEnd();
        int cols=(int)(b.w/26.f); if(cols<1) cols=1;
        int rows=(int)(b.h/30.f); if(rows<1) rows=1;
        float wx=b.w/(cols+1), wy=b.h/(rows+1);
        for(int row=0; row<rows; ++row)
            for(int col=0; col<cols; ++col){
                float wbx=b.x+wx*(col+0.5f)-5.f, wby=b.y+wy*(row+0.5f)-4.f;
                bool lit=nightMode&&((row*5+col*3)%3!=0);
                glColor3f(lit?0.98f:0.28f, lit?0.90f:0.38f, lit?0.50f:0.72f);
                glBegin(GL_QUADS);
                  glVertex2f(wbx,wby); glVertex2f(wbx+10,wby);
                  glVertex2f(wbx+10,wby+9); glVertex2f(wbx,wby+9);
                glEnd();
            }
        glColor3f(0.04f,0.04f,0.06f);
        glBegin(GL_LINE_LOOP);
          glVertex2f(b.x,b.y); glVertex2f(b.x+b.w,b.y); glVertex2f(b.x+b.w,b.y+b.h); glVertex2f(b.x,b.y+b.h);
        glEnd();
    }
}

// ============================================================
//  TRAFFIC LIGHTS
// ============================================================
void drawTrafficLight(float tx, float by)
{
    glColor3f(0.26f,0.26f,0.26f);
    glBegin(GL_QUADS);
      glVertex2f(tx-4,by); glVertex2f(tx+4,by); glVertex2f(tx+4,by+120); glVertex2f(tx-4,by+120);
    glEnd();
    glColor3f(0.10f,0.10f,0.10f);
    glBegin(GL_QUADS);
      glVertex2f(tx-14,by+70); glVertex2f(tx+14,by+70); glVertex2f(tx+14,by+122); glVertex2f(tx-14,by+122);
    glEnd();
    bool redOn=(signalPhase==0), yellowOn=(signalPhase==1), greenOn=(signalPhase==2);
    glColor3f(redOn?1.f:0.22f, 0.f, 0.f);                              filledCircle(tx,by+114,8);
    glColor3f(yellowOn?0.98f:0.28f, yellowOn?0.78f:0.28f, 0.f);        filledCircle(tx,by+100,8);
    glColor3f(0.f, greenOn?(nightMode?1.f:0.85f):0.20f, 0.f);          filledCircle(tx,by+86,8);
    if(nightMode){
        glEnable(GL_BLEND); glBlendFunc(GL_SRC_ALPHA,GL_ONE_MINUS_SRC_ALPHA);
        if(redOn)    { glColor4f(1.f,0.0f,0.0f,0.30f); filledCircle(tx,by+114,18,16); }
        if(yellowOn) { glColor4f(1.f,0.8f,0.0f,0.30f); filledCircle(tx,by+100,18,16); }
        if(greenOn)  { glColor4f(0.f,1.0f,0.0f,0.25f); filledCircle(tx,by+86, 18,16); }
        glDisable(GL_BLEND);
    }
    glColor3f(0.06f,0.06f,0.06f);
    for(int h=0; h<3; ++h){
        float ly=by+86+h*14;
        glBegin(GL_QUADS);
          glVertex2f(tx-14,ly+9); glVertex2f(tx+14,ly+9);
          glVertex2f(tx+14,ly+13); glVertex2f(tx-14,ly+13);
        glEnd();
    }
}
void drawDresdenSign()
{
    float depth = 0.30f;
    float y     = depth * HORIZON;
    float sc    = 1.f - depth * 0.75f;
    float bw = 200.f * sc;
    float bh =  68.f * sc;
    float rightEdge = roadR(y) + 40.f * sc;
    float sx = rightEdge - bw;
    float sy = y + 270.f * sc;
    float postW = 5.f * sc;
    float postX = sx + bw - 14.f * sc;

    glColor3f(0.55f, 0.55f, 0.57f);
    glBegin(GL_QUADS);
      glVertex2f(postX - postW, y); glVertex2f(postX + postW, y);
      glVertex2f(postX + postW, sy); glVertex2f(postX - postW, sy);
    glEnd();
    glColor3f(0.08f, 0.08f, 0.10f);
    glBegin(GL_QUADS);
      glVertex2f(sx + 4.f*sc,       sy - 4.f*sc);
      glVertex2f(sx + bw + 4.f*sc,  sy - 4.f*sc);
      glVertex2f(sx + bw + 4.f*sc,  sy + bh - 4.f*sc);
      glVertex2f(sx + 4.f*sc,       sy + bh - 4.f*sc);
    glEnd();
    glColor3f(0.04f, 0.18f, 0.52f);
    glBegin(GL_QUADS);
      glVertex2f(sx,      sy);      glVertex2f(sx + bw, sy);
      glVertex2f(sx + bw, sy + bh); glVertex2f(sx,      sy + bh);
    glEnd();
    glColor3f(0.95f, 0.95f, 0.95f);
    glLineWidth(2.5f * sc);
    glBegin(GL_LINE_LOOP);
      glVertex2f(sx + 3.f*sc,      sy + 3.f*sc);
      glVertex2f(sx + bw - 3.f*sc, sy + 3.f*sc);
      glVertex2f(sx + bw - 3.f*sc, sy + bh - 3.f*sc);
      glVertex2f(sx + 3.f*sc,      sy + bh - 3.f*sc);
    glEnd();
    glLineWidth(1.0f);
    glBegin(GL_LINE_LOOP);
      glVertex2f(sx + 6.f*sc,      sy + 6.f*sc);
      glVertex2f(sx + bw - 6.f*sc, sy + 6.f*sc);
      glVertex2f(sx + bw - 6.f*sc, sy + bh - 6.f*sc);
      glVertex2f(sx + 6.f*sc,      sy + bh - 6.f*sc);
    glEnd();
    glColor3f(0.95f, 0.95f, 0.95f);
    drawText(sx + 12.f*sc, sy + bh * 0.60f, "Dresden", GLUT_BITMAP_HELVETICA_18);
    drawText(sx + 12.f*sc, sy + bh * 0.22f, "50 km",   GLUT_BITMAP_HELVETICA_12);
}

// ============================================================
//  BILLBOARD (3D with name engraving)
// ============================================================
void drawBillboard3D(float bx, float by)
{
    float bw=192.f, bh=74.f, dep=24.f, ph=72.f;
    glColor3f(0.30f,0.24f,0.14f);
    glBegin(GL_QUADS);
      glVertex2f(bx+18,by); glVertex2f(bx+26,by); glVertex2f(bx+26,by+ph); glVertex2f(bx+18,by+ph);
    glEnd();
    glBegin(GL_QUADS);
      glVertex2f(bx+bw-26,by); glVertex2f(bx+bw-18,by); glVertex2f(bx+bw-18,by+ph); glVertex2f(bx+bw-26,by+ph);
    glEnd();
    glColor3f(0.10f,0.08f,0.06f);
    glBegin(GL_QUADS);
      glVertex2f(bx+bw,by+ph); glVertex2f(bx+bw+dep,by+ph-dep*0.44f);
      glVertex2f(bx+bw+dep,by+ph+bh-dep*0.44f); glVertex2f(bx+bw,by+ph+bh);
    glEnd();
    glColor3f(0.18f,0.15f,0.10f);
    glBegin(GL_QUADS);
      glVertex2f(bx,by+ph+bh); glVertex2f(bx+bw,by+ph+bh);
      glVertex2f(bx+bw+dep,by+ph+bh-dep*0.44f); glVertex2f(bx+dep,by+ph+bh-dep*0.44f);
    glEnd();
    glColor3f(0.04f,0.04f,0.04f);
    glBegin(GL_QUADS);
      glVertex2f(bx,by+ph); glVertex2f(bx+bw,by+ph); glVertex2f(bx+bw,by+ph+bh); glVertex2f(bx,by+ph+bh);
    glEnd();
    glColor3f(0.88f,0.72f,0.10f); glLineWidth(3.f);
    glBegin(GL_LINE_LOOP);
      glVertex2f(bx+4,by+ph+4); glVertex2f(bx+bw-4,by+ph+4);
      glVertex2f(bx+bw-4,by+ph+bh-4); glVertex2f(bx+4,by+ph+bh-4);
    glEnd();
    glLineWidth(1.f);
    glColor3f(0.98f,0.84f,0.12f); drawText(bx+54,by+ph+46,"AHMAD",GLUT_BITMAP_HELVETICA_18);
    glColor3f(0.96f,0.96f,0.96f); drawText(bx+28,by+ph+18,"THE  INVINCIBLE",GLUT_BITMAP_HELVETICA_12);
    glColor3f(0.50f,0.50f,0.52f);
    filledCircle(bx+40,by+ph+bh,5); filledCircle(bx+bw-40,by+ph+bh,5);
    if(nightMode){
        glEnable(GL_BLEND); glBlendFunc(GL_SRC_ALPHA,GL_ONE_MINUS_SRC_ALPHA);
        glColor4f(1.f,0.97f,0.70f,0.20f);
        filledCircle(bx+40,by+ph+bh,30,20); filledCircle(bx+bw-40,by+ph+bh,30,20);
        glDisable(GL_BLEND);
    }
    glColor3f(1.f,0.97f,0.70f);
    filledCircle(bx+40,by+ph+bh,4); filledCircle(bx+bw-40,by+ph+bh,4);
}

// ============================================================
//  SPEED STREAKS
// ============================================================
void drawSpeedStreaks()
{
    glEnable(GL_BLEND); glBlendFunc(GL_SRC_ALPHA,GL_ONE_MINUS_SRC_ALPHA);
    unsigned int s=31337u;
    for(int i=0; i<26; ++i){
        s=s*1664525u+1013904223u; float y=(s&0xFFF)/4095.f*(HORIZON-20.f)+10.f;
        s=s*1664525u+1013904223u; float len=60.f+(s&0xFF)/255.f*200.f;
        s=s*1664525u+1013904223u; float x0=(s&0xFFF)/4095.f*WIN_W;
        float alp=0.04f+(s&0xFF)/255.f*0.06f;
        glColor4f(1.f,1.f,1.f,alp);
        glBegin(GL_LINES); glVertex2f(x0,y); glVertex2f(x0+len,y); glEnd();
    }
    glDisable(GL_BLEND); glLineWidth(1.f);
}

// ============================================================
//  BMW SEDAN — REAR VIEW (vehicle block)
// ============================================================
void drawBMWRear(float cx, float cy)
{
    const float S=0.90f;
    float bR=nightMode?0.32f:0.52f, bG=nightMode?0.33f:0.54f, bB=nightMode?0.36f:0.58f;
    float darkR=bR*0.60f, darkG=bG*0.60f, darkB=bB*0.60f;
    float lightR=fminf(bR+0.14f,1.f), lightG=fminf(bG+0.14f,1.f), lightB=fminf(bB+0.14f,1.f);
    glColor3f(darkR*0.80f,darkG*0.80f,darkB*0.82f);
    glBegin(GL_POLYGON);
      glVertex2f(cx-118.f*S,cy); glVertex2f(cx+118.f*S,cy);
      glVertex2f(cx+106.f*S,cy+22.f*S); glVertex2f(cx-106.f*S,cy+22.f*S);
    glEnd();
    glColor3f(0.08f,0.08f,0.09f);
    glBegin(GL_POLYGON);
      glVertex2f(cx-50.f*S,cy+2.f*S); glVertex2f(cx+50.f*S,cy+2.f*S);
      glVertex2f(cx+44.f*S,cy+18.f*S); glVertex2f(cx-44.f*S,cy+18.f*S);
    glEnd();
    glColor3f(0.20f,0.20f,0.22f); glLineWidth(1.2f);
    for(int f=-4; f<=4; ++f){
        float fx=cx+f*10.f*S;
        glBegin(GL_LINES); glVertex2f(fx,cy+3.f*S); glVertex2f(fx+f*0.8f*S,cy+17.f*S); glEnd();
    }
    glLineWidth(1.f);
    float epR=7.5f*S, epLX=cx-62.f*S, epRX=cx+62.f*S, epY=cy+11.f*S;
    glColor3f(0.70f,0.70f,0.74f); filledCircle(epLX,epY,epR+2.f*S); filledCircle(epRX,epY,epR+2.f*S);
    glColor3f(0.10f,0.10f,0.10f); filledCircle(epLX,epY,epR); filledCircle(epRX,epY,epR);
    if(nightMode){
        glEnable(GL_BLEND); glBlendFunc(GL_SRC_ALPHA,GL_ONE_MINUS_SRC_ALPHA);
        glColor4f(1.f,0.30f,0.02f,0.45f);
        filledCircle(epLX,epY,epR*0.7f,12); filledCircle(epRX,epY,epR*0.7f,12);
        glDisable(GL_BLEND);
    }
    glColor3f(0.07f,0.07f,0.08f);
    glBegin(GL_QUADS);
      glVertex2f(cx-106.f*S,cy+4.f*S); glVertex2f(cx-66.f*S,cy+4.f*S);
      glVertex2f(cx-68.f*S,cy+20.f*S); glVertex2f(cx-108.f*S,cy+20.f*S);
    glEnd();
    glBegin(GL_QUADS);
      glVertex2f(cx+66.f*S,cy+4.f*S); glVertex2f(cx+106.f*S,cy+4.f*S);
      glVertex2f(cx+108.f*S,cy+20.f*S); glVertex2f(cx+68.f*S,cy+20.f*S);
    glEnd();
    glColor3f(0.22f,0.22f,0.24f); glLineWidth(1.f);
    for(int v=1; v<=3; ++v){
        float vy=cy+(4.f+v*4.f)*S;
        glBegin(GL_LINES); glVertex2f(cx-106.f*S,vy); glVertex2f(cx-66.f*S,vy); glEnd();
        glBegin(GL_LINES); glVertex2f(cx+66.f*S,vy);  glVertex2f(cx+106.f*S,vy); glEnd();
    }
    glColor3f(bR,bG,bB);
    glBegin(GL_POLYGON);
      glVertex2f(cx-118.f*S,cy+22.f*S); glVertex2f(cx+118.f*S,cy+22.f*S);
      glVertex2f(cx+122.f*S,cy+60.f*S); glVertex2f(cx+116.f*S,cy+90.f*S);
      glVertex2f(cx-116.f*S,cy+90.f*S); glVertex2f(cx-122.f*S,cy+60.f*S);
    glEnd();
    glColor3f(lightR,lightG,lightB);
    glBegin(GL_QUADS);
      glVertex2f(cx-100.f*S,cy+50.f*S); glVertex2f(cx+100.f*S,cy+50.f*S);
      glVertex2f(cx+96.f*S, cy+56.f*S); glVertex2f(cx-96.f*S, cy+56.f*S);
    glEnd();
    float tlY1=cy+80.f*S, tlY2=cy+88.f*S;
    glColor3f(nightMode?0.95f:0.72f,0.02f,0.02f);
    glBegin(GL_QUADS);
      glVertex2f(cx-112.f*S,tlY1); glVertex2f(cx+112.f*S,tlY1);
      glVertex2f(cx+112.f*S,tlY2); glVertex2f(cx-112.f*S,tlY2);
    glEnd();
    glColor3f(nightMode?0.98f:0.78f,0.03f,0.03f);
    glBegin(GL_POLYGON);
      glVertex2f(cx-112.f*S,tlY1); glVertex2f(cx-82.f*S,tlY1);
      glVertex2f(cx-78.f*S,cy+98.f*S); glVertex2f(cx-114.f*S,cy+98.f*S);
    glEnd();
    glBegin(GL_QUADS);
      glVertex2f(cx-82.f*S,tlY1); glVertex2f(cx-52.f*S,tlY1);
      glVertex2f(cx-52.f*S,tlY2); glVertex2f(cx-82.f*S,tlY2);
    glEnd();
    glColor3f(nightMode?0.98f:0.78f,0.03f,0.03f);
    glBegin(GL_POLYGON);
      glVertex2f(cx+82.f*S,tlY1); glVertex2f(cx+112.f*S,tlY1);
      glVertex2f(cx+114.f*S,cy+98.f*S); glVertex2f(cx+78.f*S,cy+98.f*S);
    glEnd();
    glBegin(GL_QUADS);
      glVertex2f(cx+52.f*S,tlY1); glVertex2f(cx+82.f*S,tlY1);
      glVertex2f(cx+82.f*S,tlY2); glVertex2f(cx+52.f*S,tlY2);
    glEnd();
    glColor3f(nightMode?0.98f:0.82f,nightMode?0.65f:0.50f,0.0f);
    glBegin(GL_QUADS);
      glVertex2f(cx-114.f*S,tlY1); glVertex2f(cx-102.f*S,tlY1);
      glVertex2f(cx-100.f*S,cy+98.f*S); glVertex2f(cx-114.f*S,cy+98.f*S);
    glEnd();
    glBegin(GL_QUADS);
      glVertex2f(cx+102.f*S,tlY1); glVertex2f(cx+114.f*S,tlY1);
      glVertex2f(cx+114.f*S,cy+98.f*S); glVertex2f(cx+100.f*S,cy+98.f*S);
    glEnd();
    glColor3f(0.05f,0.05f,0.05f); glLineWidth(1.2f);
    for(int d=1; d<=4; ++d){
        float dx=cx-112.f*S+d*7.f*S;
        glBegin(GL_LINES); glVertex2f(dx,tlY1); glVertex2f(dx-0.5f,cy+98.f*S); glEnd();
    }
    for(int d=1; d<=4; ++d){
        float dx=cx+112.f*S-d*7.f*S;
        glBegin(GL_LINES); glVertex2f(dx,tlY1); glVertex2f(dx+0.5f,cy+98.f*S); glEnd();
    }
    glLineWidth(1.f);
    if(nightMode){
        glEnable(GL_BLEND); glBlendFunc(GL_SRC_ALPHA,GL_ONE_MINUS_SRC_ALPHA);
        glColor4f(1.f,0.08f,0.08f,0.28f);
        glBegin(GL_QUADS);
          glVertex2f(cx-120.f*S,tlY1-8.f*S); glVertex2f(cx-48.f*S,tlY1-8.f*S);
          glVertex2f(cx-48.f*S,cy+104.f*S);  glVertex2f(cx-120.f*S,cy+104.f*S);
        glEnd();
        glBegin(GL_QUADS);
          glVertex2f(cx+48.f*S,tlY1-8.f*S);  glVertex2f(cx+120.f*S,tlY1-8.f*S);
          glVertex2f(cx+120.f*S,cy+104.f*S); glVertex2f(cx+48.f*S,cy+104.f*S);
        glEnd();
        glDisable(GL_BLEND);
    }
    glColor3f(bR*0.92f,bG*0.92f,bB*0.94f);
    glBegin(GL_POLYGON);
      glVertex2f(cx-114.f*S,cy+90.f*S); glVertex2f(cx+114.f*S,cy+90.f*S);
      glVertex2f(cx+108.f*S,cy+130.f*S); glVertex2f(cx-108.f*S,cy+130.f*S);
    glEnd();
    glColor3f(0.80f,0.80f,0.84f);
    glBegin(GL_QUADS);
      glVertex2f(cx-110.f*S,cy+90.f*S); glVertex2f(cx+110.f*S,cy+90.f*S);
      glVertex2f(cx+108.f*S,cy+96.f*S); glVertex2f(cx-108.f*S,cy+96.f*S);
    glEnd();
    glColor3f(0.95f,0.95f,0.98f); glLineWidth(1.5f);
    glBegin(GL_LINES); glVertex2f(cx-110.f*S,cy+92.f*S); glVertex2f(cx+110.f*S,cy+92.f*S); glEnd();
    glLineWidth(1.f);
    glColor3f(lightR,lightG,lightB);
    glBegin(GL_QUADS);
      glVertex2f(cx-80.f*S,cy+100.f*S); glVertex2f(cx+80.f*S,cy+100.f*S);
      glVertex2f(cx+76.f*S,cy+106.f*S); glVertex2f(cx-76.f*S,cy+106.f*S);
    glEnd();
    glColor3f(nightMode?0.12f:0.20f, nightMode?0.14f:0.24f, nightMode?0.18f:0.32f);
    glBegin(GL_POLYGON);
      glVertex2f(cx-102.f*S,cy+130.f*S); glVertex2f(cx+102.f*S,cy+130.f*S);
      glVertex2f(cx+72.f*S,cy+190.f*S);  glVertex2f(cx-72.f*S,cy+190.f*S);
    glEnd();
    glColor3f(0.06f,0.06f,0.07f);
    glBegin(GL_QUADS);
      glVertex2f(cx-108.f*S,cy+126.f*S); glVertex2f(cx-98.f*S,cy+126.f*S);
      glVertex2f(cx-70.f*S,cy+192.f*S);  glVertex2f(cx-80.f*S,cy+192.f*S);
    glEnd();
    glBegin(GL_QUADS);
      glVertex2f(cx+98.f*S,cy+126.f*S);  glVertex2f(cx+108.f*S,cy+126.f*S);
      glVertex2f(cx+80.f*S,cy+192.f*S);  glVertex2f(cx+70.f*S,cy+192.f*S);
    glEnd();
    glColor3f(0.28f,0.32f,0.42f); glLineWidth(1.f);
    for(int el=1; el<=7; ++el){
        float ely=cy+130.f*S+el*8.f*S, ewL=cx-100.f*S+el*3.f*S, ewR=cx+100.f*S-el*3.f*S;
        glBegin(GL_LINES); glVertex2f(ewL,ely); glVertex2f(ewR,ely); glEnd();
    }
    glColor3f(bR*0.88f,bG*0.88f,bB*0.90f);
    glBegin(GL_POLYGON);
      glVertex2f(cx-72.f*S,cy+190.f*S); glVertex2f(cx+72.f*S,cy+190.f*S);
      glVertex2f(cx+56.f*S,cy+216.f*S); glVertex2f(cx-56.f*S,cy+216.f*S);
    glEnd();
    glColor3f(0.12f,0.12f,0.14f);
    glBegin(GL_TRIANGLES);
      glVertex2f(cx-4.f*S,cy+208.f*S); glVertex2f(cx+4.f*S,cy+208.f*S); glVertex2f(cx,cy+228.f*S);
    glEnd();
    glColor3f(darkR,darkG,darkB);
    glBegin(GL_POLYGON);
      glVertex2f(cx-116.f*S,cy+165.f*S); glVertex2f(cx-138.f*S,cy+162.f*S);
      glVertex2f(cx-140.f*S,cy+155.f*S); glVertex2f(cx-118.f*S,cy+152.f*S);
    glEnd();
    glColor3f(nightMode?0.14f:0.25f, nightMode?0.16f:0.28f, nightMode?0.22f:0.38f);
    glBegin(GL_QUADS);
      glVertex2f(cx-117.f*S,cy+163.f*S); glVertex2f(cx-135.f*S,cy+160.f*S);
      glVertex2f(cx-136.f*S,cy+156.f*S); glVertex2f(cx-119.f*S,cy+154.f*S);
    glEnd();
    glColor3f(darkR,darkG,darkB);
    glBegin(GL_POLYGON);
      glVertex2f(cx+116.f*S,cy+165.f*S); glVertex2f(cx+138.f*S,cy+162.f*S);
      glVertex2f(cx+140.f*S,cy+155.f*S); glVertex2f(cx+118.f*S,cy+152.f*S);
    glEnd();
    glColor3f(nightMode?0.14f:0.25f, nightMode?0.16f:0.28f, nightMode?0.22f:0.38f);
    glBegin(GL_QUADS);
      glVertex2f(cx+117.f*S,cy+163.f*S); glVertex2f(cx+135.f*S,cy+160.f*S);
      glVertex2f(cx+136.f*S,cy+156.f*S); glVertex2f(cx+119.f*S,cy+154.f*S);
    glEnd();
    float badgeX=cx, badgeY=cy+112.f*S, badgeR=13.f*S;
    glColor3f(0.82f,0.82f,0.86f); filledCircle(badgeX,badgeY,badgeR);
    glColor3f(0.10f,0.10f,0.12f); filledCircle(badgeX,badgeY,badgeR*0.90f);
    glColor3f(0.95f,0.95f,0.95f);
    glBegin(GL_QUADS);
      glVertex2f(badgeX-badgeR*0.88f,badgeY-badgeR*0.10f); glVertex2f(badgeX+badgeR*0.88f,badgeY-badgeR*0.10f);
      glVertex2f(badgeX+badgeR*0.88f,badgeY+badgeR*0.10f); glVertex2f(badgeX-badgeR*0.88f,badgeY+badgeR*0.10f);
    glEnd();
    glBegin(GL_QUADS);
      glVertex2f(badgeX-badgeR*0.10f,badgeY-badgeR*0.88f); glVertex2f(badgeX+badgeR*0.10f,badgeY-badgeR*0.88f);
      glVertex2f(badgeX+badgeR*0.10f,badgeY+badgeR*0.88f); glVertex2f(badgeX-badgeR*0.10f,badgeY+badgeR*0.88f);
    glEnd();
    glColor3f(0.04f,0.28f,0.72f);
    glBegin(GL_TRIANGLE_FAN); glVertex2f(badgeX,badgeY);
    for(int k=0; k<=20; ++k){ float a=PI*0.5f+k*(PI*0.5f/20); glVertex2f(badgeX+badgeR*0.88f*cosf(a),badgeY+badgeR*0.88f*sinf(a)); }
    glEnd();
    glBegin(GL_TRIANGLE_FAN); glVertex2f(badgeX,badgeY);
    for(int k=0; k<=20; ++k){ float a=PI*1.5f+k*(PI*0.5f/20); glVertex2f(badgeX+badgeR*0.88f*cosf(a),badgeY+badgeR*0.88f*sinf(a)); }
    glEnd();
    glColor3f(0.96f,0.96f,0.96f);
    glBegin(GL_TRIANGLE_FAN); glVertex2f(badgeX,badgeY);
    for(int k=0; k<=20; ++k){ float a=0.f+k*(PI*0.5f/20); glVertex2f(badgeX+badgeR*0.88f*cosf(a),badgeY+badgeR*0.88f*sinf(a)); }
    glEnd();
    glBegin(GL_TRIANGLE_FAN); glVertex2f(badgeX,badgeY);
    for(int k=0; k<=20; ++k){ float a=PI+k*(PI*0.5f/20); glVertex2f(badgeX+badgeR*0.88f*cosf(a),badgeY+badgeR*0.88f*sinf(a)); }
    glEnd();
    glColor3f(0.82f,0.82f,0.86f);
    ringArc(badgeX,badgeY,badgeR,0,2*PI,badgeR*0.12f,32);
}

// ============================================================
//  MAIN DISPLAY — draws all layers in order
// ============================================================
void display()
{
    glClear(GL_COLOR_BUFFER_BIT);
    glMatrixMode(GL_PROJECTION); glLoadIdentity();
    gluOrtho2D(0, WIN_W, 0, WIN_H);
    glMatrixMode(GL_MODELVIEW); glLoadIdentity();

    drawSky();
    drawHills();
    drawGround();
    drawCityBuildings();
    drawRoadSideBuildings();
    drawRoad();
    drawSidewalks();
    drawTreeRows();
    drawLampRows();
    drawLaneMarkings();
    drawDresdenSign();
    drawSpeedStreaks();

    drawTrafficLight( 74.f, 22.f);
    drawTrafficLight(1020.f, 22.f);

    drawBillboard3D(-30.f, 360.f);
    drawBillboard3D(870.f, 360.f);

    drawBMWRear(550.f + carX, 30.f);

    glutSwapBuffers();
}

// ============================================================
//  TIMER — animation tick (33ms ≈ 30 fps)
// ============================================================
void timer(int)
{
    laneOffset += 5.f;
    if(laneOffset > 300.f) laneOffset = 0.f;

    cloudOffset += 0.4f;
    if(cloudOffset > 1260.f) cloudOffset = 0.f;

    signalTimer++;
    if(signalTimer >= 90){ signalTimer = 0; signalPhase = (signalPhase+1)%3; }

    glutPostRedisplay();
    glutTimerFunc(33, timer, 0);
}

// ============================================================
//  INPUT — keyboard controls
// ============================================================
void specialKeys(int key, int, int)
{
    if(key == GLUT_KEY_LEFT)  carX -= 15.f;
    if(key == GLUT_KEY_RIGHT) carX += 15.f;
    if(carX < -320) carX = -320;
    if(carX >  320) carX =  320;
    glutPostRedisplay();
}

void normalKeys(unsigned char key, int, int)
{
    if(key == 'n' || key == 'N') nightMode = !nightMode;
    if(key == 27) exit(0);
    glutPostRedisplay();
}
// ============================================================
//  MAIN
// ============================================================
int main(int argc, char** argv)
{
    glutInit(&argc, argv);
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB);
    glutInitWindowSize(WIN_W, WIN_H);
    glutInitWindowPosition(60, 50);
    glutCreateWindow("BMW City Drive - Ahmad The Invincible");
    glClearColor(0.f, 0.f, 0.f, 1.f);
    glutDisplayFunc(display);
    glutSpecialFunc(specialKeys);
    glutKeyboardFunc(normalKeys);
    glutTimerFunc(33, timer, 0);
    glutMainLoop();
    return 0;
}

