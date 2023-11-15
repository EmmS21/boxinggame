<script>
    import { writable } from 'svelte/store';
    import { onMount } from 'svelte';
    export let fightResultData
    import BetBoxingBanner from './BetBoxingBanner.svelte';
    let goBack = writable(false);
    let currentValue;
    fightResultData.subscribe(value => {
        currentValue = value
    })()

    let firstHalf, firstHalfStats, secondHalf, secondHalfStats, outcome;

    if (currentValue && currentValue.response) {
        const responseText = currentValue.response;
        
        const firstHalfMatch = responseText.match(/First Half:[\s\S]*?(?=First Half Stats:)/);
        const firstHalfStatsMatch = responseText.match(/First Half Stats:[\s\S]*?(?=Second Half:)/);
        const secondHalfMatch = responseText.match(/Second Half:[\s\S]*?(?=Second Half Stats:)/);
        const secondHalfStatsMatch = responseText.match(/Second Half Stats:[\s\S]*?(?=Outcome:)/);
        const outcomeMatch = responseText.match(/Outcome:[\s\S]*$/);

        firstHalf = firstHalfMatch ? firstHalfMatch[0].replace('First Half:', '').trim() : '';
        firstHalfStats = firstHalfStatsMatch ? firstHalfStatsMatch[0].replace('First Half Stats:', '').trim() : '';
        secondHalf = secondHalfMatch ? secondHalfMatch[0].replace('Second Half:', '').trim() : '';
        secondHalfStats = secondHalfStatsMatch ? secondHalfStatsMatch[0].replace('Second Half Stats:', '').trim() : '';
        outcome = outcomeMatch ? outcomeMatch[0].replace('Outcome:', '').trim() : '';
    }

    function returnBack() {
        goBack(true)  
    }

    onMount(() => {
        const textElements = ['firstHalf', 'firstHalfStats', 'secondHalf', 'secondHalfStats', 'outcome'];
        const headers = [
        'First 5 rounds',
        'First 5 rounds - Statistics',
        'Final 5 rounds',
        'Final 5 rounds - Statistics',
        'Final Outcome'
        ];
        let currentIndex = 0;

        function animateText() {
            if (currentIndex >= textElements.length) return;
            let element = document.getElementById(textElements[currentIndex]);
            let header = document.getElementById(`header${currentIndex}`);
            header.classList.add('typewriter');
            header.style.opacity = '1';
            setTimeout(() => {
                header.style.opacity = '0';
                setTimeout(() => {
                    if (currentIndex < textElements.length -1) {
                        document.getElementById(`header${currentIndex + 1}`).classList.add('typewriter');
                    }
                    element.style.opacity = '1';
                    setTimeout(() => {
                        element.style.opacity = '0';
                        currentIndex++;
                        animateText();
                    }, 5000); 
                }, 4000); 
            }, 2000);
        }

        animateText();
    });
</script>

<style>
    .white-background {
        background-color: white;
        color: black;
        padding: 1rem;
        width: 100%;
        height: 100vh;
        position: relative; 
        text-align: center;
        display: flex;
        justify-content: center;
        align-items: center;
        flex-direction: column;
    }
    .circle-button {
        margin-top: 1rem; 
        display: inline-block; 
        width: 100px; 
        height: 100px; 
        line-height: 100px; 
        border: 2px solid black; 
        border-radius: 50%;
        font-size: 50px; 
        text-align: center; 
        position: absolute;
        top: 1rem;
        left: 50%; 
        transform: translateX(-50%); 
        cursor: pointer; 
        background-color: white; 
        transition: transform 0.3s; 
        z-index: 10
    }
    @keyframes pulsate {
        from {
           box-shadow: 0 0 0 0 rgba(0, 0, 0, 0.7);
        }
        to {
            box-shadow: 0 0 0 15px rgba(0, 0, 0, 0);
        }
    }
    .circle-button:hover {
        animation: pulsate 1.5s infinite alternate;
    }
    @keyframes typing {
        from { width: 0 }
        to { width: 100% }
    }
    @keyframes fadeOut {
        from { opacity: 1; }
        to { opacity: 0; }
    }
    .typewriter {
        overflow: hidden;
        border-right: .15em solid black;
        white-space: nowrap;
        margin: 0 auto;
        letter-spacing: .15em;
        animation: 
        typing 2s steps(40, end),
        fadeOut 1s 2s forwards;
    }
    #firstHalf, #firstHalfStats, #secondHalf, #secondHalfStats, #outcome {
        opacity: 0;
        transition: opacity 4s;
        position: fixed; 
        top: 50%; 
        left: 50%;
        transform: translate(-50%, -50%);
    }
    #header0, #header1, #header2, #header3, #header4 {
        opacity: 0;
        transition: opacity 4s;
        position: fixed; 
        top: 50%; 
        left: 50%;
        transform: translate(-50%, -50%);
        width: 200px;
        height: 200px;
    }
    .content-wrapper {
        text-align: center;
        position: relative; /* Ensure that .content-wrapper is positioned in context to .centered-container */
    } 

</style>
{#if $goBack}
    <BetBoxingBanner />
{:else}
<div class="white-background">
    <button class="circle-button" on:click={()=>returnBack}>&times;</button> 
    <h2 id="header0">First 5 rounds</h2>
    <p id="firstHalf">{firstHalf}</p>
    <h2 id="header1">First 5 rounds - Statistics</h2>
    <p id="firstHalfStats">{firstHalfStats}</p>
    <h2 id="header2">Final 5 rounds</h2>
    <p id="secondHalf">{secondHalf}</p>
    <h2 id="header3">Final 5 rounds - Statistics</h2>
    <p id="secondHalfStats">{secondHalfStats}</p>
    <h2 id="header4">Final Outcome</h2>
    <p id="outcome">{outcome}</p>
</div>
{/if}