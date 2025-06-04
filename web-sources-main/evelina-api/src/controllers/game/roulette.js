const models = {
  BET_NUMBER_MIN: 0,
  BET_NUMBER_MAX: 36,
  BET_NUMBER_MID: 18,
  BetType: {
    number: 'number',
    color_green: 'color_green',
    color_rb: 'color_rb',
    parity: 'parity',
    dozen: 'dozen',
  },
  BetColor: {
    red: 'red',
    black: 'black',
    green: 'green',
  },
  BetParity: {
    even: 'even',
    odd: 'odd',
  },
  BetDozen: {
    low: 'low',
    middle: 'middle',
    high: 'high',
  },
  NUMBERS_RED: [1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36],
  NUMBERS_BLACK: [2, 4, 6, 8, 10, 11, 13, 15, 17, 20, 22, 24, 26, 28, 29, 31, 33, 35],
  NUMBERS_GREEN: [0],
  PAYOUT_MULTIPLIERS: {
    number: 36,
    color_rb: 2,
    parity: 2,
    color_green: 36,
    dozen: 3,
  }
};

function validateBet(bet) {
  bet = bet.toLowerCase();
  if (!isNaN(bet)) {
    bet = parseInt(bet);
    if (bet < models.BET_NUMBER_MIN || bet > models.BET_NUMBER_MAX) {
      return false;
    }
    return models.BetType.number;
  } else if (Object.values(models.BetColor).includes(bet)) {
    return bet === models.BetColor.green ? models.BetType.color_green : models.BetType.color_rb;
  } else if (Object.values(models.BetParity).includes(bet)) {
    return models.BetType.parity;
  } else if (Object.values(models.BetDozen).includes(bet)) {
    return models.BetType.dozen;
  }
  return false;
}

function getNumberParity(num) {
  return num % 2 === 0 ? models.BetParity.even : models.BetParity.odd;
}

function getNumberColor(num) {
  if (models.NUMBERS_RED.includes(num)) {
    return models.BetColor.red;
  } else if (models.NUMBERS_BLACK.includes(num)) {
    return models.BetColor.black;
  } else if (models.NUMBERS_GREEN.includes(num)) {
    return models.BetColor.green;
  }
  return false;
}

function getNumberDozen(num) {
  if (num >= 1 && num <= 12) {
    return models.BetDozen.low;
  } else if (num >= 13 && num <= 24) {
    return models.BetDozen.middle;
  } else if (num >= 25 && num <= 36) {
    return models.BetDozen.high;
  }
  return null;
}

function checkBetWin(bet, roll) {
  if (bet.type === models.BetType.parity) {
    return roll.parity === bet.bet;
  } else if ([models.BetType.color_rb, models.BetType.color_green].includes(bet.type)) {
    return roll.color === bet.bet;
  } else if (bet.type === models.BetType.number) {
    return roll.number === parseInt(bet.bet);
  } else if (bet.type === models.BetType.dozen) {
    return roll.dozen === bet.bet;
  }
  return false;
}

function play(bet, wager) {
  const roll = {
    number: Math.floor(Math.random() * 37),
  };
  roll.color = getNumberColor(roll.number);
  roll.parity = getNumberParity(roll.number);
  roll.dozen = getNumberDozen(roll.number);

  bet.type = validateBet(bet.bet);
  const didWin = checkBetWin(bet, roll);
  const payoutRate = didWin ? models.PAYOUT_MULTIPLIERS[bet.type] : 0;
  const payoutAmount = wager * payoutRate;

  return {
    success: true,
    roll: {
      number: roll.number,
      color: roll.color,
      parity: roll.parity,
      dozen: roll.dozen,
    },
    bet: {
      bet: bet.bet,
      wager: wager.toFixed(2),
      win: didWin,
      payout_rate: payoutRate,
      payout: payoutAmount.toFixed(2),
    },
  };
}

const rouletteController = {
  play: async (req, res) => {
    const { bet, amount } = req.query;

    if (!bet) {
      return res.status(400).json({ error: '400', message: 'Parameter "bet" is required' });
    }

    if (!amount) {
      return res.status(400).json({ error: '400', message: 'Parameter "amount" is required' });
    }

    try {
      const result = play({ bet }, parseFloat(amount));
      res.json(result);
    } catch (err) {
      res.status(500).json({ error: '500', message: 'Error processing the Roulette bet' });
    }
  }
};

module.exports = {
  rouletteController
};