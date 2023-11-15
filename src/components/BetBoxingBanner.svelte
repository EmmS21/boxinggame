<script>
    import { onMount } from 'svelte';
    import { writable } from 'svelte/store';
    import '../styles/BetBoxingBanner.css';
    import '../styles/LightningBolt.css';
    import FightOutcome from './FightOutcome.svelte';


    let currentDate = new Date().toLocaleDateString();
    let fightsToday = writable([]);
    let fightsTodaySnapshot = [];
    let showModal = writable(false);
    let selectedFighters = writable({});
    let fighterDetails = writable({});
    let fightsOdds = writable(new Map());
    let bettingOddsWinValues = writable({});
    let userBalance = writable(0);
    let showButtons = true;
    let sliderValues = writable({});
    let betType = '';
    let showFightOutcome = writable(false);
    let fightResultData = writable(null);
    let isLoading = writable(false);


    function handleSliderInput(event, fightId) {
        const value = event.target.value;
        sliderValues.update(values => ({ ...values, [fightId]: value }));
    }

    function calculateWinner(fighter1Stats, fighter2Stats, odds){
        return fighter1Stats.name
    }

    async function generateWinner(fighter1, fighter2, odds) {
        try {
            isLoading.set(true)
            let fightStats = await fetchFighterDetails(fighter1, fighter2)
            fightStats.odds = odds

            fightStats.fighter1 = {
                name: fighter1,
                bouts_fought: fightStats[fighter1].bouts_fought,
                wins: fightStats[fighter1].wins.replace('Wins: ', ''),
                win_by_knockout: fightStats[fighter1].win_by_knockout,
                losses: fightStats[fighter1].losses.replace('Losses: ', ''),
                average_weight: fightStats[fighter1].average_weight.replace('Average Weight: ', '')
            };

            fightStats.fighter2 = {
                name: fighter2,
                bouts_fought: fightStats[fighter2].bouts_fought,
                wins: fightStats[fighter2].wins.replace('Wins: ', ''),
                win_by_knockout: fightStats[fighter2].win_by_knockout,
                losses: fightStats[fighter2].losses.replace('Losses: ', ''),
                average_weight: fightStats[fighter2].average_weight.replace('Average Weight: ', '')
            };

            const fightDataJSON = JSON.stringify({
                fighter1: fightStats.fighter1,
                fighter2: fightStats.fighter2,
                odds: fightStats.odds
            });

            console.log('Formatted fightStats for POST request:', fightDataJSON);
            
            const response = await fetch('http://127.0.0.1:8000/start_fight', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                credentials: 'include',
                body: fightDataJSON
            })
            if(!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`)
            }
            const data = await response.json()
            console.log('data',data)
            fightResultData.set(data)
            showFightOutcome.set(true)
            isLoading.set(false)
            return data
        } catch (error) {
            console.error('Error fetching fighter details:', error)
        }
    }


    async function confirmBet(fightId) {
        const betAmount = $sliderValues[fightId];
        if (betAmount) {
            console.log('bet', betAmount)
            userBalance = userBalance - betAmount
            sliderValues = { ...sliderValues, [fightId]: betAmount };
        }
        fightsToday.update(fights => {
            return fights.map(fight => {
                if (fight.id === fightId) {
                    return { ...fight, showButtons: false, showBetAmount: true };
                }
                return fight;
            });
        });
    }


    $: if ($showModal) {
        // When the modal is shown, fetch the fighter details
        fetchFighterDetails($selectedFighters.fighter1, $selectedFighters.fighter2)
            .then(details => {
                Object.keys(details).forEach(fighter => {
                    details[fighter].average_weight = parseFloat(details[fighter].average_weight.replace('Average Weight: ', ''));
                    details[fighter].wins = parseFloat(details[fighter].wins.replace('Wins: ', ''));
                    details[fighter].losses = parseFloat(details[fighter].losses.replace('Losses: ', ''));
                });
                console.log('details', details)
                fighterDetails.set(details);
            })
            .catch(error => {
                console.error("There was a problem retrieving fighter details:", error);
                fighterDetails.set({}); 
            });
    }

    function getDivisionColor(division) {
        const colors = {
            heavy: 'red',
            cruiser: 'blue',
            bantam: 'purple',
            fly: 'green',
            'super middle': 'orange',
            middle: 'cyan',
            'super light': 'lightblue',
            welter: 'gray',
            light: 'magenta',
            'super welter': 'brown',
            'super bantam': 'lime',
            feather: 'silver',
            'super feather': 'gold',
            'light heavy': 'bisque',
            'super fly': 'teal',
            'light fly': 'fuchsia',
            'minimum': 'violet'
        };
        return colors[division.toLowerCase()] || 'default';
    }

    async function fetchFighterDetails(fighter1, fighter2) {
        try {
            const response = await fetch('http://127.0.0.1:8000/get_fighter_details', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                credentials: 'include',
                body: JSON.stringify({ fighter1, fighter2 })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            return data;
        } catch (error) {
            console.error("There was a problem retrieving fighter details:", error);
        }
    }

    function divisionClass(division) {
        return `tag tag-${division.replace(/\s+/g, '-').toLowerCase()}`;
    }

    function openModal(fighterOne, fighterTwo) {
        let nameOne = fighterOne.name
        let nameTwo = fighterTwo.name
        selectedFighters.set({ fighter1: nameOne, fighter2: nameTwo })
        showModal.set(true);
    }

    function calculateAmericanOdds(probability) {
        if(probability < 0.5) {
            return '+' + Math.round(100 / (1 / probability - 1));
        } else {
            return '-' + Math.round((probability / (1 - probability)) * 100);
        }
    }

    function calculateWinnings(odds, betAmount) {
        let americanOdds = calculateAmericanOdds(odds)
        let winnings = 0;
        if (americanOdds.startsWith('+')) {
            let numericOdds = parseInt(americanOdds.substring(1));
            winnings = (numericOdds / 100) * betAmount;
        } else if (americanOdds.startsWith('-')) {
            let numericOdds = parseInt(americanOdds.substring(1));
            winnings = betAmount / (numericOdds / 100);
        }
        return winnings;
    }


    onMount(async () => {
        const response = await fetch('http://127.0.0.1:8000/fightstoday', {
            credentials: 'include',
        });
        const data = await response.json();

        const groupedFighters = data.reduce((acc, fighter) => {
            const key = `${fighter.division}_${fighter.sex}`;
            if (!acc[key]) {
                acc[key] = [];
            }
            acc[key].push(fighter);
            return acc;
        }, {});

        // Flatten the groups into a list of fighters that have at least one other fighter in the same division and sex
        const matchingFighters = Object.values(groupedFighters)
                                    .filter(group => group.length >= 2)
                                    .flat()
                                    .map(fighter => ({ ...fighter, showButtons: true }))

        // Set the store's value, which should trigger the component to update
        fightsToday.set(matchingFighters);

        // Fetch betting odds for each pair
        for (const [index, fighter1] of matchingFighters.entries()) {
            for (const fighter2 of matchingFighters.slice(index + 1)) {
                if (fighter1.division === fighter2.division && fighter1.sex === fighter2.sex) {
                    const oddsData = await getBettingOdds(fighter1.name, fighter2.name);
                    const fightPairKey = `${fighter1.name} vs ${fighter2.name}`;
                    bettingOddsWinValues.update(values => {
                        values[fightPairKey] = {
                            win: oddsData.win,
                            loss: oddsData.loss,
                            draw: oddsData.draw
                        }
                        return values;
                    });
                }
            }
        }

        const balanceResponse = await fetch('http://127.0.0.1:8000/balance', {
            credentials: 'include',
        });
        if (balanceResponse.ok) {
            const balanceData = await balanceResponse.json();
            userBalance = balanceData.balance;
        } else {
            // Handle errors
        }
    });

    async function getBettingOdds(fighter1, fighter2) {
        console.log('fighter', fighter1, fighter2)
        try {
        const response = await fetch('http://127.0.0.1:8000/predict', {
            method: 'POST',
            headers: {
            'Content-Type': 'application/json',
            },
            credentials: 'include',
            body: JSON.stringify({ fighter1, fighter2 }),
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        // Handle the received odds data
        console.log('Odds data:', data);
        return data
        } catch (error) {
        console.error('Error fetching betting odds:', error);
        }
    }

    function toggleDisplay(selectedFight, type) {
        if (type) {
            betType = type;
        }
        fightsToday.update(allFights => {
            return allFights.map(fight => {
                if (fight.id === selectedFight.id) {
                    // Toggle showButtons for the selected fight
                    return { ...fight, showButtons: !fight.showButtons, showBetAmount: false };
                }
                // Keep the same state for other fights
                return fight;
            });
        });
    }


    // Reactive assignment to keep fightsTodaySnapshot updated
    $: fightsTodaySnapshot = $fightsToday;

    let buttonText = 'Fight';

    function handleMouseOver() {
        buttonText = "Let's get ready to Rumble!";
    }

    function handleMouseOut() {
        buttonText = "Fight";
    }
</script>

<style>
    .button-hover-text {
        display: none;
    }
    button:hover .button-hover-text {
        display: initial;
    }
    button:hover .button-original-text {
        display: none;
    }
    .disabled-button {
    background-color: gray;
    pointer-events: none; /* This will ensure that hover effects don't work when the button is disabled */
  }
</style>
{#if $isLoading}
    <div class="loading-screen">
        Please wait....
    </div>
{:else}
    {#if $showFightOutcome}
        <FightOutcome {fightResultData} />
    {:else}
    <div class="bet-boxing-banner">
        <h1>Bet Boxing</h1>
        <p>Bet money, watch daily fights and let our machine learning model pick a winner based on up to date boxing stats<p>
                {#if $showModal}
                <div class="modal-background">
                    <div class="modal" style="border: 1px solid #eee;">
                        <button on:click={() => showModal.set(false)}
                                style="font-size: 2em; line-height: 0.5; width: 50px; height: 50px; top: 10px; right: 10px; border: none; background: transparent; cursor: pointer;">
                            &times; <!-- HTML entity for 'X' -->
                        </button>
                        <h2>
                            <span style="font-weight: bold; font-size: 1.5em;">Tale</span>
                            <span style="font-size: 0.8em;">of the</span>
                            <span style="font-weight: bold; font-size: 1.5em;">Tape</span>
                        </h2>
                        <div style="display: flex; justify-content: space-around;">
                            
                            <!-- Fighter 1 Stats -->
                            <div style="flex: 1; display: flex; flex-direction: column; align-items: center; padding-right: 20px;">
                                <h3>{$selectedFighters.fighter1}</h3>
                                {#if $fighterDetails[$selectedFighters.fighter1]}
                                    <div style="background: linear-gradient(to right, #89f7fe, #66a6ff); padding: 2.5px; margin-bottom: 5px;">
                                        <p>{$fighterDetails[$selectedFighters.fighter1].bouts_fought}</p>
                                    </div>
                                    <div style="background: linear-gradient(to right, #89f7fe, #66a6ff); padding: 2.5px; margin-bottom: 5px;">
                                        <p>{$fighterDetails[$selectedFighters.fighter1].wins}</p>
                                    </div>
                                    <div style="background: linear-gradient(to right, #89f7fe, #66a6ff); padding: 2.5px; margin-bottom: 5px;">
                                        <p>{$fighterDetails[$selectedFighters.fighter1].win_by_knockout}</p>
                                    </div>
                                    <div style="background: linear-gradient(to right, #89f7fe, #66a6ff); padding: 2.5px; margin-bottom: 5px;">
                                    <p>{$fighterDetails[$selectedFighters.fighter1].losses}</p>
                                    </div>
                                    <div style="background: linear-gradient(to right, #89f7fe, #66a6ff); padding: 2.5px; margin-bottom: 5px;">
                                    <p>{$fighterDetails[$selectedFighters.fighter1].average_weight.toFixed(2)} lbs</p>
                                    </div>
                                {/if}
                            </div>

                            <!-- Headers -->
                            <div style="flex: 0.5; display: flex; flex-direction: column; align-items: center;">
                                <h3 style="visibility: hidden;">Alignment Header</h3> <!-- Invisible header for alignment -->
                                <p style="background: linear-gradient(to right, #d4fc79, #96e6a1); padding: 5px; width: 100%; text-align: center;">Bouts fought</p>
                                <p style="background: linear-gradient(to right, #d4fc79, #96e6a1); padding: 5px; width: 100%; text-align: center;">Wins</p>
                                <p style="background: linear-gradient(to right, #d4fc79, #96e6a1); padding: 5px; width: 100%; text-align: center;">Wins by Knockout</p>
                                <p style="background: linear-gradient(to right, #d4fc79, #96e6a1); padding: 5px; width: 100%; text-align: center;">Losses</p>
                                <p style="background: linear-gradient(to right, #d4fc79, #96e6a1); padding: 5px; width: 100%; text-align: center;">Average Weight</p>
                            </div>
                            
                            <!-- Fighter 2 Stats -->
                            <div style="flex: 1; display: flex; flex-direction: column; align-items: center;">
                                <h3>{$selectedFighters.fighter2}</h3>
                                {#if $fighterDetails[$selectedFighters.fighter2]}
                                <div style="background: linear-gradient(to right, #89f7fe, #66a6ff); padding: 2.5px; margin-bottom: 5px;">
                                    <p>{$fighterDetails[$selectedFighters.fighter2].bouts_fought}</p>
                                </div>
                                <div style="background: linear-gradient(to right, #89f7fe, #66a6ff); padding: 2.5px; margin-bottom: 5px;">
                                    <p>{$fighterDetails[$selectedFighters.fighter2].wins}</p>
                                </div>
                                <div style="background: linear-gradient(to right, #89f7fe, #66a6ff); padding: 2.5px; margin-bottom: 5px;">
                                    <p>{$fighterDetails[$selectedFighters.fighter2].win_by_knockout}</p>
                                </div>
                                <div style="background: linear-gradient(to right, #89f7fe, #66a6ff); padding: 2.5px; margin-bottom: 5px;">
                                    <p>{$fighterDetails[$selectedFighters.fighter2].losses}</p>
                                </div>
                                <div style="background: linear-gradient(to right, #89f7fe, #66a6ff); padding: 2.5px; margin-bottom: 5px;">
                                    <p>{$fighterDetails[$selectedFighters.fighter2].average_weight.toFixed(2)} lbs</p>
                                </div>
                                {/if}
                            </div>
                        </div>
                    </div>
                </div>
            {/if}

        <div class="fight-table">
            <div class="table-header">Today's fights {currentDate}</div>
            <p class="instruction-text">
                Bet on the fighter you believe will win, see how much you will win based on betting odds, click Let's go and watch a live commentary of the fight
            </p>
            <div class="rows">
            {#each $fightsToday as fight, index (fight.name)}
                {#if index % 2 === 0} 
                    <div class="row">
                        <div class="section section-1">
                            <b>Division:</b> 
                            <span class={divisionClass(fight.division)} 
                                style="background-color: {getDivisionColor(fight.division)};">
                                {fight.division}
                            </span><br>
                            <b>Gender:</b> {fight.sex}
                        </div>
                        <div class="section section-2" on:click={() => openModal(fight,$fightsToday[index + 1])}>
                            {fight.name} vs {fightsTodaySnapshot[index + 1]?.name}
                        </div>
                        <div class="section section-3">Make Bet
                            {#if $fightsToday[index].showButtons && !$fightsToday[index].showBetAmount}
                                <div class="bet-buttons">
                                    <button class="bet-button" on:click={e => { e.stopPropagation(); toggleDisplay(fight, 'Win'); }}>Win</button>
                                    <button class="bet-button" on:click={e => { e.stopPropagation(); toggleDisplay(fight, 'Loss'); }}>Loss</button>
                                    <button class="bet-button" on:click={e => { e.stopPropagation(); toggleDisplay(fight, 'Draw'); }}>Draw</button>
                                </div>
                            {:else}
                                {#if $fightsToday[index].showBetAmount}
                                    <div class="bet-amount-display">
                                        <span>Bet Amount: $ {$sliderValues[fight.id]} for {betType} </span>
                                    </div>
                                {:else}
                                    <div class="{($fightsToday[index].showButtons ? '' : 'hidden')} slider-container">
                                        <button class="close-button" on:click={toggleDisplay(fight)}>X</button>
                                        <input type="range" min="1" max={userBalance} 
                                            bind:value={$sliderValues[fight.id]}
                                            on:input={e => handleSliderInput(e, fight.id)} 
                                        />
                                        <span class="slider-value">$ {$sliderValues[fight.id] || 0}</span>
                                        <button class="bet-button" on:click={() => confirmBet(fight.id)}>
                                            Confirm {betType} Bet
                                        </button>
                                    </div>
                                {/if}
                            {/if}
                        </div>

                        <div class="section section-4">
                            Betting Odds:
                            <div>
                                Win: 
                                <span>
                                    {@html $bettingOddsWinValues[`${fight.name} vs ${$fightsToday[index + 1]?.name}`]?.win 
                                        ? calculateAmericanOdds($bettingOddsWinValues[`${fight.name} vs ${$fightsToday[index + 1]?.name}`]?.win) 
                                        : '<span class="placeholder">Calculating...</span>'}
                                </span>
                            </div>
                            <div>
                                Loss: 
                                <span>
                                    {@html $bettingOddsWinValues[`${fight.name} vs ${$fightsToday[index + 1]?.name}`]?.loss 
                                        ? calculateAmericanOdds($bettingOddsWinValues[`${fight.name} vs ${$fightsToday[index + 1]?.name}`]?.loss) 
                                        : '<span class="placeholder">Calculating...</span>'}
                                </span>
                            </div>
                            <div>
                                Draw: 
                                <span>
                                    {@html $bettingOddsWinValues[`${fight.name} vs ${$fightsToday[index + 1]?.name}`]?.draw 
                                        ? calculateAmericanOdds($bettingOddsWinValues[`${fight.name} vs ${$fightsToday[index + 1]?.name}`]?.draw) 
                                        : '<span class="placeholder">Calculating...</span>'}
                                </span>
                            </div>
                        </div>
                        <div class="section section-5">
                            {#if $fightsToday[index].showBetAmount}
                                <div class="bet-amount" style="color: green;">
                                    ${($sliderValues[fight.id] + calculateWinnings($bettingOddsWinValues[`${fight.name} vs ${$fightsToday[index + 1]?.name}`]?.[betType.toLowerCase()], $sliderValues[fight.id])).toFixed(2)} for {betType}
                                </div>
                            {/if}
                            <button 
                                on:mouseover={handleMouseOver} 
                                on:mouseout={handleMouseOut}
                                disabled={!$fightsToday[index].showBetAmount}
                                class:disabled={!$fightsToday[index].showBetAmount}
                                on:click={() => generateWinner(fight.name, $fightsToday[index + 1]?.name, $bettingOddsWinValues[`${fight.name} vs ${$fightsToday[index + 1]?.name}`])}
                            >
                                {$fightsToday[index].showBetAmount ? buttonText : 'Make a Bet first'}
                            </button>
                        </div>
                    </div>
                {/if}
            {/each}
            </div>
        </div>
        <div class="balance">
            Your balance is: ${userBalance}
        </div>
    </div>
    {/if}
{/if}