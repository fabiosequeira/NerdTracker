import { exchangeRefreshTokenForAuthTokens, getTitleTrophies } from "psn-api";

const refreshToken = "e773405a-b9af-4137-87fe-b7d4fbcee7bd"; // from auth step

const main = async () => {
  const authorization = await exchangeRefreshTokenForAuthTokens(refreshToken);

  // Example: Ghost of Tsushima Directors Cut (just replace with any NPWR ID you need)
  const npCommunicationId = "NPWR20113_00"; 

  const response = await getTitleTrophies(authorization, npCommunicationId, "all", {
    npServiceName: "trophy",
    limit: 100,
  });

  console.log(JSON.stringify(response, null, 2));
};

main();
