import {mkdir,writeFile} from 'node:fs/promises';
import {runTests} from '../tests/editor.mjs';
const result=runTests(),out=new URL('../build-cs/',import.meta.url);
await mkdir(out,{recursive:true});
await writeFile(new URL('editor-test-export.zip',out),result.zip);
await writeFile(new URL('editor-tests.json',out),JSON.stringify({checks:result.checks},null,2)+'\n');
console.log(result.checks.join('\n'));
