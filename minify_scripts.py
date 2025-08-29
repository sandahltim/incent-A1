#!/usr/bin/env python3
"""
Script to minify JavaScript files with proper handling of audio paths and interaction requirements
"""

import re
import json

def minify_js(content):
    """Basic JavaScript minification"""
    # Remove comments (but preserve important ones like version info)
    content = re.sub(r'//(?![^\n]*Version:)[^\n]*', '', content)
    content = re.sub(r'/\*[\s\S]*?\*/', '', content)
    
    # Remove unnecessary whitespace
    content = re.sub(r'\s+', ' ', content)
    content = re.sub(r';\s*', ';', content)
    content = re.sub(r'{\s*', '{', content)
    content = re.sub(r'\s*}', '}', content)
    content = re.sub(r',\s*', ',', content)
    content = re.sub(r':\s*', ':', content)
    content = re.sub(r'\s*=\s*', '=', content)
    content = re.sub(r'\s*\+\s*', '+', content)
    content = re.sub(r'\s*-\s*', '-', content)
    content = re.sub(r'\s*\*\s*', '*', content)
    content = re.sub(r'\s*/\s*', '/', content)
    content = re.sub(r'\s*&&\s*', '&&', content)
    content = re.sub(r'\s*\|\|\s*', '||', content)
    content = re.sub(r'\s*!\s*', '!', content)
    content = re.sub(r'\s*\(\s*', '(', content)
    content = re.sub(r'\s*\)\s*', ')', content)
    content = re.sub(r'\s*\[\s*', '[', content)
    content = re.sub(r'\s*\]\s*', ']', content)
    
    # Remove trailing semicolons before closing braces
    content = re.sub(r';}', '}', content)
    
    return content.strip()

def create_safe_minified_script():
    """Create a minified script.js with proper audio handling"""
    
    # Read the original script.js
    with open('/home/tim/incentDev/static/script.js', 'r') as f:
        script_content = f.read()
    
    # Add the audio interaction handler at the beginning
    audio_handler = """
// Audio Interaction Handler - Inline version for script.min.js
(function(){
    let userInteracted=false;
    let pendingAudio=[];
    window.AudioInteractionManager={
        hasUserInteracted:()=>userInteracted,
        safePlay:(audio,label)=>{
            if(!audio)return Promise.reject('No audio');
            if(audio.readyState<2)audio.load();
            if(userInteracted){
                return audio.play().catch(err=>{
                    if(!err.message.includes('user didn\\'t interact'))console.warn(`${label||'Audio'} failed:`,err);
                    return Promise.reject(err);
                });
            }else{
                pendingAudio.push(()=>audio.play().catch(err=>console.warn(`${label||'Audio'} deferred failed:`,err)));
                return Promise.resolve();
            }
        },
        markUserInteraction:()=>{
            if(!userInteracted){
                userInteracted=true;
                console.log('Audio enabled');
                while(pendingAudio.length>0){
                    try{pendingAudio.shift()();}catch(e){}
                }
                if(window.casinoAudio&&window.casinoAudio.handleUserInteraction)window.casinoAudio.handleUserInteraction();
            }
        }
    };
    ['click','touchstart','touchend','keydown','mousedown'].forEach(e=>document.addEventListener(e,evt=>{
        if(evt.isTrusted)window.AudioInteractionManager.markUserInteraction();
    },{once:false,passive:true,capture:true}));
})();
"""
    
    # Combine and minify
    full_content = audio_handler + "\n" + script_content
    minified = minify_js(full_content)
    
    # Write the minified version
    with open('/home/tim/incentDev/static/script.min.js', 'w') as f:
        f.write(minified)
    
    print("Created minified script.min.js with audio interaction handling")
    
    # Also create a minified vegas-casino.js
    with open('/home/tim/incentDev/static/vegas-casino.js', 'r') as f:
        vegas_content = f.read()
    
    vegas_minified = minify_js(vegas_content)
    
    with open('/home/tim/incentDev/static/vegas-casino.min.js', 'w') as f:
        f.write(vegas_minified)
    
    print("Created minified vegas-casino.min.js")

if __name__ == "__main__":
    create_safe_minified_script()