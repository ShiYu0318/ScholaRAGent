// GitHub 風卡片：細邊框、6px 圓角、header + body。
import { Box, Heading, Spinner, Text } from "@primer/react";
import type { Icon } from "@primer/octicons-react";
import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";

interface CardProps {
  title: string;
  icon?: Icon;
  action?: ReactNode;
  children: ReactNode;
}

export function Card({ title, icon: IconComp, action, children }: CardProps) {
  return (
    <Box
      sx={{
        border: "1px solid",
        borderColor: "border.default",
        borderRadius: 2,
        bg: "canvas.default",
        display: "flex",
        flexDirection: "column",
        minHeight: 140,
      }}
    >
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          gap: 2,
          px: 3,
          py: 2,
          borderBottom: "1px solid",
          borderColor: "border.muted",
          bg: "canvas.subtle",
          borderTopLeftRadius: 2,
          borderTopRightRadius: 2,
        }}
      >
        {IconComp && (
          <Text sx={{ color: "fg.muted", display: "flex" }}>
            <IconComp size={16} />
          </Text>
        )}
        <Heading as="h3" sx={{ fontSize: 1, flex: 1 }}>
          {title}
        </Heading>
        {action}
      </Box>
      <Box sx={{ p: 3, flex: 1 }}>{children}</Box>
    </Box>
  );
}

export function CardState({ loading, error, empty }: { loading?: boolean; error?: boolean; empty?: boolean }) {
  const { t } = useTranslation();
  if (loading) {
    return (
      <Box display="flex" justifyContent="center" p={2}>
        <Spinner size="small" />
      </Box>
    );
  }
  if (error) return <Text sx={{ color: "fg.subtle", fontSize: 1 }}>{t("common.unavailable")}</Text>;
  if (empty) return <Text sx={{ color: "fg.subtle", fontSize: 1 }}>{t("common.empty")}</Text>;
  return null;
}
