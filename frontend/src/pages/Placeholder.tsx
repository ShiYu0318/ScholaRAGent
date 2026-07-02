// 尚未實作頁面的暫位元件：後續各階段逐一替換。
import { Box, Heading, Text } from "@primer/react";
import { useTranslation } from "react-i18next";

export function Placeholder({ titleKey }: { titleKey: string }) {
  const { t } = useTranslation();
  return (
    <Box>
      <Heading as="h2" sx={{ fontSize: 3, mb: 2 }}>
        {t(titleKey)}
      </Heading>
      <Box
        sx={{
          border: "1px dashed",
          borderColor: "border.default",
          borderRadius: 2,
          p: 5,
          textAlign: "center",
        }}
      >
        <Text sx={{ color: "fg.muted" }}>{t("common.unavailable")}</Text>
      </Box>
    </Box>
  );
}
