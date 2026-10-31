import {encodeBackground} from './core.mjs';
self.onmessage=e=>{try{const result=encodeBackground(e.data);self.postMessage(result,[result.raw.buffer,result.rgba.buffer]);}catch(error){self.postMessage({error:error.message});}};
