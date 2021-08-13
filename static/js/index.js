let searchInput = document.getElementById('search-input');
let form = document.getElementById('search-form');
let optionList = document.getElementById('listid');
let optionMap = {}

let searchTimer = null;

searchInput.oninput = ()=>{
    if(searchInput.value.startsWith('\u2009')){
        //console.log(optionMap[searchInput.value]);
        window.location.href = `/video/${optionMap[searchInput.value]}`
        return;
    }
    optionList.innerHTML = '';
    if (searchTimer){
        clearInterval(searchTimer)
    }
    searchTimer = setTimeout(()=>{
        if(searchInput.value.trim()){
            fetch(`/api/suggestion/${searchInput.value.trim()}`)
                .then((response)=>response.json())
                .then((data)=>{
                    options = {}
                    data.results.forEach((d)=>{
                        let ee = document.createElement('option');
                        ee.setAttribute('data-value', d['video_id']);
                        ee.value = '\u2009' + d['video_name'];
                        optionMap['\u2009' + d['video_name']] = d['video_id'];
                        optionList.appendChild(ee)
                    });
                    optionList.setAttribute('size', optionList.options.length);
                })
        }
    }, 400)
}

window.onscroll = function(ev) {
    if ((window.innerHeight + window.scrollY) >= document.body.offsetHeight) {
        fetch('/api/content')
            .then((response)=>response.json())
            .then((data)=>{
            data.forEach((d)=>{
            let div = document.createElement('div');
            div.innerHTML = `<div class="card my-4">
            <a href="/video/${d['id']}">
                <img src="/thumbnail/${d['id']}" class="card-img-top" alt="${d['file_name']}">
            </a>
            <div class="card-body">
                <h5 class="card-title">${d['file_name'].toLowerCase().replace( /\b./g, function(a){ return a.toUpperCase(); } )}</h5>
                <p class="card-text text-muted">Duration: ${d['duration'].split('.')[0]}</p>
            </div>
        </div>`
            document.getElementById('suggestion').appendChild(div);
            });
            });
    }
};