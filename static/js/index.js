let searchInput = document.getElementById('search-input');
let form = document.getElementById('search-form');
let optionList = document.getElementById('listid');

let searchTimer = null;

searchInput.oninput = ()=>{
    optionList.innerHTML = '';
    if (searchTimer){
        clearInterval(searchTimer)
    }
    searchTimer = setTimeout(()=>{
        if(searchInput.value.trim()){
            fetch(`/api/suggestion/${searchInput.value.trim()}`)
                .then((response)=>response.json())
                .then((data)=>{
                    data.results.forEach((d)=>{
                        let ee = document.createElement('option');
                        ee.setAttribute('data-value', d['video_id']);
                        ee.value = d['video_name'];
                        ee.setAttribute('onclick', "console.log(e, 'hi')");
                        optionList.appendChild(ee)
                    });
                    optionList.setAttribute('size', optionList.options.length);
                })
        }
    }, 400)
}