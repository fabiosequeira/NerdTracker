import { exchangeNpssoForCode, exchangeCodeForAccessToken } from "psn-api";

const npsso = "GVVWlrbewAvAjVcqEmWwiriRhjuJhhomRAxQ3GOMSeX58jTguLjt8g6HsqbJTVVA";

const main = async () => {
  const accessCode = await exchangeNpssoForCode(npsso);
  const authorization = await exchangeCodeForAccessToken(accessCode);

  console.log("Authorization:", authorization);
};

main();
