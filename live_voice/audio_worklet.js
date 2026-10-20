'use strict';
class YumiAudio extends AudioWorkletProcessor {
  constructor(){
    super();this.epoch=0;this.queue=[];this.queued=0;this.offset=0;this.phase=0;this.pending=0;
    this.capture=new Int16Array(640);this.captured=0;this.inputPhase=0;this.inputSum=0;this.inputCount=0;this.tick=0;this.audible=false;this.energy=0;
    this.port.onmessage=({data})=>{
      if(data.kind==='clear'){
        this.epoch=data.epoch;this.queue=[];this.queued=0;this.offset=0;this.phase=0;this.pending=0;this.audible=false;
      } else if(data.kind==='audio'&&data.epoch===this.epoch){
        this.pending=Math.max(0,this.pending-1);
        if(this.queued>24000*.16){this.port.postMessage({kind:'fault'});return;}
        this.queue.push({pcm:new Int16Array(data.pcm),count:data.count/2});this.queued+=data.pcm.byteLength/2;
      }
    };
  }
  process(inputs,outputs){
    const input=inputs[0]?.[0],output=outputs[0][0];
    for(let i=0;i<output.length;i++){
      if(input){
        this.inputSum+=input[i];this.inputCount++;this.inputPhase+=16000/sampleRate;
        if(this.inputPhase>=1){
          this.inputPhase-=1;const value=Math.max(-1,Math.min(1,this.inputSum/this.inputCount));this.inputSum=0;this.inputCount=0;
          this.capture[this.captured++]=Math.round(value*32767);
          if(this.captured===640){const pcm=this.capture.buffer;this.port.postMessage({kind:'mic',pcm},[pcm]);this.capture=new Int16Array(640);this.captured=0;}
        }
      }
      const chunk=this.queue[0];
      if(chunk){
        output[i]=chunk.pcm[this.offset]/32768;
        if(this.offset<chunk.count)this.audible=true;
        this.phase+=24000/sampleRate;
        if(this.phase>=1){this.phase-=1;this.offset++;this.queued--;}
        if(this.offset>=chunk.pcm.length){this.queue.shift();this.offset=0;}
      }else output[i]=0;
      this.energy+=output[i]*output[i];
      if(++this.tick>=sampleRate*.02){
        this.port.postMessage({kind:'played',audible:this.audible,epoch:this.epoch,level:Math.sqrt(this.energy/this.tick||0)});this.audible=false;this.energy=0;this.tick=0;
        while(this.queued+this.pending*480<1440){this.pending++;this.port.postMessage({kind:'pull',epoch:this.epoch});}
      }
    }
    return true;
  }
}
registerProcessor('yumi-audio',YumiAudio);
